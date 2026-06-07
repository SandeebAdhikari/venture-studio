"""Worker process lifecycle and database session helpers."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from uuid import uuid4

from app.config import Settings, get_settings
from app.db.session import close_db, get_session_factory, init_db
from app.logging import get_logger
from app.observability.setup import init_observability
from app.observability.worker_heartbeat import clear_worker_heartbeat, refresh_worker_heartbeat
from app.redis.client import close_redis, get_redis_client, init_redis
from app.repositories import RepositoryContainer, get_repositories
from app.services.container import ServiceContainer

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = get_logger(__name__)


async def worker_startup(ctx: dict) -> None:
    """Initialize shared resources when an ARQ worker starts."""
    settings = get_settings()
    init_observability(settings)
    init_db(settings)
    init_redis(settings)

    from app.founder_fit.matrix_loader import init_mechanism_requirement_matrix

    init_mechanism_requirement_matrix()
    ctx["redis"] = get_redis_client()
    ctx["worker_id"] = uuid4().hex

    from app.collectors.hn_algolia import register_hn_algolia_collector
    from app.collectors.reddit import register_reddit_collector
    from app.collectors.rss import register_rss_collector

    register_reddit_collector(redis=ctx["redis"])
    register_rss_collector(redis=ctx["redis"])
    register_hn_algolia_collector(redis=ctx["redis"])

    await refresh_worker_heartbeat(ctx["redis"], ctx["worker_id"], settings=settings)

    async def heartbeat_loop() -> None:
        while True:
            await asyncio.sleep(max(settings.worker_heartbeat_ttl_sec // 3, 10))
            await refresh_worker_heartbeat(ctx["redis"], ctx["worker_id"], settings=settings)

    ctx["heartbeat_task"] = asyncio.create_task(heartbeat_loop())
    logger.info("ARQ worker started", extra={"worker_id": ctx["worker_id"]})


async def worker_shutdown(ctx: dict) -> None:
    """Release resources when an ARQ worker stops."""
    heartbeat_task = ctx.get("heartbeat_task")
    if heartbeat_task is not None:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

    redis = ctx.get("redis")
    worker_id = ctx.get("worker_id")
    if redis is not None and worker_id:
        await clear_worker_heartbeat(redis, worker_id, settings=ctx.get("settings"))

    await close_db()
    await close_redis()
    logger.info("ARQ worker stopped", extra={"worker_id": ctx.get("worker_id")})


@asynccontextmanager
async def worker_session() -> AsyncGenerator[tuple[ServiceContainer, RepositoryContainer], None]:
    """Provide a committed database session for a background job."""
    factory = get_session_factory()
    async with factory() as session:
        repos = get_repositories(session)
        services = ServiceContainer(repos)
        try:
            yield services, repos
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_worker_redis(ctx: dict) -> Redis:
    redis = ctx.get("redis")
    if redis is None:
        return get_redis_client()
    return redis


def get_worker_settings(ctx: dict) -> Settings:
    return ctx.get("settings") or get_settings()
