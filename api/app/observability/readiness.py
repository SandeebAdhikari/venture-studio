"""Expanded readiness checks for production dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

from app.config import Settings
from app.logging import get_logger
from app.observability.alerting.status import check_alerting_status
from app.scheduler.scheduler import get_scheduler

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.worker_heartbeat import list_active_workers

logger = get_logger(__name__)


class ReadinessCheckResult:
    __slots__ = ("name", "status", "detail")

    def __init__(self, name: str, status: str, detail: str | None = None) -> None:
        self.name = name
        self.status = status
        self.detail = detail


async def check_postgresql(db: AsyncSession) -> ReadinessCheckResult:
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        return ReadinessCheckResult(name="postgresql", status="ok")
    except Exception as exc:
        logger.warning("PostgreSQL readiness check failed", exc_info=exc)
        return ReadinessCheckResult(name="postgresql", status="error", detail=str(exc))


async def check_redis(redis: Redis) -> ReadinessCheckResult:
    try:
        pong = await redis.ping()
        if pong:
            return ReadinessCheckResult(name="redis", status="ok")
        return ReadinessCheckResult(
            name="redis",
            status="error",
            detail="PING did not return True",
        )
    except Exception as exc:
        logger.warning("Redis readiness check failed", exc_info=exc)
        return ReadinessCheckResult(name="redis", status="error", detail=str(exc))


async def check_worker_availability(
    redis: Redis,
    settings: Settings,
) -> ReadinessCheckResult:
    if not settings.worker_readiness_required:
        return ReadinessCheckResult(
            name="worker",
            status="ok",
            detail="not required",
        )

    try:
        workers = await list_active_workers(redis, settings=settings)
        if workers:
            return ReadinessCheckResult(
                name="worker",
                status="ok",
                detail=f"{len(workers)} active",
            )
        return ReadinessCheckResult(
            name="worker",
            status="error",
            detail="no active worker heartbeats",
        )
    except Exception as exc:
        logger.warning("Worker readiness check failed", exc_info=exc)
        return ReadinessCheckResult(name="worker", status="error", detail=str(exc))


def check_scheduler_availability(settings: Settings) -> ReadinessCheckResult:
    if not settings.scheduler_enabled:
        return ReadinessCheckResult(
            name="scheduler",
            status="ok",
            detail="disabled",
        )

    try:
        scheduler = get_scheduler()
        if scheduler.is_running:
            return ReadinessCheckResult(name="scheduler", status="ok")
        return ReadinessCheckResult(
            name="scheduler",
            status="error",
            detail="scheduler not running",
        )
    except Exception as exc:
        logger.warning("Scheduler readiness check failed", exc_info=exc)
        return ReadinessCheckResult(name="scheduler", status="error", detail=str(exc))


def check_alerting_readiness(settings: Settings) -> ReadinessCheckResult:
    result = check_alerting_status(settings)
    return ReadinessCheckResult(name=result.name, status=result.status, detail=result.detail)


async def run_readiness_checks(
    *,
    db: AsyncSession,
    redis: Redis,
    settings: Settings,
) -> list[ReadinessCheckResult]:
    return [
        await check_postgresql(db),
        await check_redis(redis),
        await check_worker_availability(redis, settings),
        check_scheduler_availability(settings),
        check_alerting_readiness(settings),
    ]
