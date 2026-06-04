"""Docker and ops health probe: verify at least one ARQ worker heartbeat in Redis."""

from __future__ import annotations

import asyncio
import sys

from app.config import get_settings
from app.observability.worker_heartbeat import list_active_workers
from app.redis.client import close_redis, init_redis


async def worker_heartbeats_healthy() -> tuple[bool, str]:
    """Return (ok, detail) when one or more worker heartbeats are present."""
    settings = get_settings()
    init_redis(settings)
    try:
        from app.redis.client import get_redis_client

        redis = get_redis_client()
        workers = await list_active_workers(redis, settings=settings)
        if workers:
            return True, f"{len(workers)} active worker(s)"
        return False, "no active worker heartbeats in Redis"
    finally:
        await close_redis()


def main() -> None:
    ok, detail = asyncio.run(worker_heartbeats_healthy())
    if ok:
        print(detail)
        raise SystemExit(0)
    print(f"ERROR: {detail}", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
