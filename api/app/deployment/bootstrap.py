"""Pre-start bootstrap: dependency waits, Alembic migrations, startup readiness."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path

import httpx
import redis as redis_lib
from sqlalchemy import create_engine, text

from app.config import Settings, get_settings
from app.db.session import close_db, get_session_factory, init_db
from app.logging import configure_logging, get_logger
from app.deployment.production_validation import enforce_production_settings
from app.observability.alerting.validation import enforce_alert_config
from app.observability.readiness import check_postgresql, check_redis
from app.redis.client import close_redis, get_redis_client, init_redis

MIGRATION_SUCCESS_MARKER = "avs_migrations_ok"

STARTUP_EXIT_MIGRATION_FAILED = 10
STARTUP_EXIT_DEPS_TIMEOUT = 11
STARTUP_EXIT_READINESS_FAILED = 12
STARTUP_EXIT_VERIFY_FAILED = 13
STARTUP_EXIT_ALERT_CONFIG_INVALID = 14
STARTUP_EXIT_PRODUCTION_CONFIG_INVALID = 15

DEFAULT_STARTUP_TIMEOUT_SEC = 120
DEFAULT_STARTUP_INTERVAL_SEC = 2.0
DEFAULT_VERIFY_TIMEOUT_SEC = 120
DEFAULT_VERIFY_INTERVAL_SEC = 2.0


def alembic_upgrade_succeeded(returncode: int, stderr: str) -> bool:
    """Return True when Alembic upgrade completed without error."""
    if returncode != 0:
        return False
    lowered = stderr.lower()
    return "traceback" not in lowered and "failed" not in lowered


def migration_marker_present(line: str, marker: str = MIGRATION_SUCCESS_MARKER) -> bool:
    """Return True when a log line contains the migration success marker."""
    return marker in line


def should_continue_waiting(elapsed_sec: float, timeout_sec: float) -> bool:
    """Return True while dependency or HTTP readiness waits may continue."""
    return elapsed_sec < timeout_sec


def next_wait_interval(attempt: int, base_interval_sec: float) -> float:
    """Compute sleep duration before the next readiness poll (bounded backoff)."""
    return min(base_interval_sec * (1 + attempt * 0.25), 10.0)


def check_postgresql_sync(settings: Settings) -> tuple[bool, str | None]:
    try:
        engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return True, None
    except Exception as exc:
        return False, str(exc)


def check_redis_sync(settings: Settings) -> tuple[bool, str | None]:
    try:
        client = redis_lib.from_url(
            settings.redis_url,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            socket_timeout=settings.redis_socket_timeout,
        )
        client.ping()
        client.close()
        return True, None
    except Exception as exc:
        return False, str(exc)


def wait_for_dependencies(
    settings: Settings,
    *,
    timeout_sec: float = DEFAULT_STARTUP_TIMEOUT_SEC,
    interval_sec: float = DEFAULT_STARTUP_INTERVAL_SEC,
) -> None:
    """Block until PostgreSQL and Redis accept connections or timeout."""
    logger = get_logger(__name__)
    start = time.monotonic()
    attempt = 0

    while should_continue_waiting(time.monotonic() - start, timeout_sec):
        pg_ok, pg_err = check_postgresql_sync(settings)
        redis_ok, redis_err = check_redis_sync(settings)
        if pg_ok and redis_ok:
            logger.info("PostgreSQL and Redis are reachable")
            return

        detail_parts = []
        if not pg_ok:
            detail_parts.append(f"postgresql: {pg_err}")
        if not redis_ok:
            detail_parts.append(f"redis: {redis_err}")
        logger.warning(
            "Waiting for dependencies",
            extra={"attempt": attempt, "detail": "; ".join(detail_parts)},
        )
        time.sleep(next_wait_interval(attempt, interval_sec))
        attempt += 1

    print(
        "ERROR: Timed out waiting for PostgreSQL/Redis. " f"timeout_sec={timeout_sec}",
        file=sys.stderr,
    )
    raise SystemExit(STARTUP_EXIT_DEPS_TIMEOUT)


def run_alembic_upgrade(*, cwd: Path | None = None) -> None:
    """Run `alembic upgrade head` and fail fast with a clear exit code."""
    logger = get_logger(__name__)
    workdir = cwd or Path.cwd()
    logger.info("Running database migrations", extra={"cwd": str(workdir)})

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)

    if not alembic_upgrade_succeeded(result.returncode, result.stderr):
        print(
            "ERROR: Alembic migration failed. " f"exit_code={result.returncode}",
            file=sys.stderr,
        )
        raise SystemExit(STARTUP_EXIT_MIGRATION_FAILED)

    print(MIGRATION_SUCCESS_MARKER)
    logger.info("Database migrations applied", extra={"marker": MIGRATION_SUCCESS_MARKER})


async def verify_in_process_readiness(settings: Settings) -> None:
    """Run PostgreSQL/Redis readiness checks before the API serves traffic."""
    alert_result = enforce_alert_config(settings)
    enforce_production_settings(settings)

    init_db(settings)
    init_redis(settings)

    try:
        async with get_session_factory()() as session:
            results = [
                await check_postgresql(session),
                await check_redis(get_redis_client()),
            ]
    finally:
        await close_redis()
        await close_db()

    failures = [item for item in results if item.status != "ok"]
    if failures:
        for item in failures:
            print(
                f"ERROR: Startup readiness failed: {item.name} "
                f"status={item.status} detail={item.detail}",
                file=sys.stderr,
            )
        raise SystemExit(STARTUP_EXIT_READINESS_FAILED)


def verify_in_process_readiness_sync(settings: Settings) -> None:
    asyncio.run(verify_in_process_readiness(settings))


def wait_for_http_readiness(
    url: str,
    *,
    timeout_sec: float = DEFAULT_VERIFY_TIMEOUT_SEC,
    interval_sec: float = DEFAULT_VERIFY_INTERVAL_SEC,
) -> None:
    """Poll an HTTP readiness URL until 200 or timeout."""
    start = time.monotonic()
    attempt = 0
    last_status: int | None = None
    last_body = ""

    while should_continue_waiting(time.monotonic() - start, timeout_sec):
        try:
            response = httpx.get(url, timeout=5.0)
            last_status = response.status_code
            last_body = response.text[:500]
            if response.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_body = str(exc)

        time.sleep(next_wait_interval(attempt, interval_sec))
        attempt += 1

    print(
        "ERROR: Readiness endpoint did not return HTTP 200 in time. "
        f"url={url} last_status={last_status} last_body={last_body!r}",
        file=sys.stderr,
    )
    raise SystemExit(STARTUP_EXIT_VERIFY_FAILED)


def bootstrap_api(settings: Settings, *, alembic_cwd: Path | None = None) -> None:
    wait_for_dependencies(settings)
    run_alembic_upgrade(cwd=alembic_cwd)
    verify_in_process_readiness_sync(settings)


def bootstrap_worker(settings: Settings) -> None:
    wait_for_dependencies(settings)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AVS API deployment bootstrap")
    parser.add_argument(
        "--mode",
        choices=("api", "worker", "verify"),
        required=True,
        help="api: migrate + readiness; worker: deps only; verify: HTTP poll",
    )
    parser.add_argument(
        "--ready-url",
        default="http://127.0.0.1:8000/health/ready",
        help="Readiness URL for --mode verify",
    )
    parser.add_argument(
        "--alembic-cwd",
        type=Path,
        default=None,
        help="Working directory for alembic (defaults to cwd)",
    )
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=DEFAULT_STARTUP_TIMEOUT_SEC,
        help="Timeout for dependency and HTTP waits",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    settings = get_settings()
    configure_logging(settings)
    alembic_cwd = args.alembic_cwd or Path.cwd()

    if args.mode == "api":
        bootstrap_api(settings, alembic_cwd=alembic_cwd)
    elif args.mode == "worker":
        bootstrap_worker(settings)
    elif args.mode == "verify":
        wait_for_http_readiness(
            args.ready_url,
            timeout_sec=args.timeout_sec,
            interval_sec=DEFAULT_VERIFY_INTERVAL_SEC,
        )


if __name__ == "__main__":
    main()
