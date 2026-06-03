"""Worker process lifecycle and database session helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from uuid import uuid4

from app.config import Settings, get_settings
from app.db.session import close_db, get_session_factory, init_db
from app.logging import get_logger
from app.redis.client import close_redis, get_redis_client, init_redis
from app.repositories import RepositoryContainer, get_repositories
from app.services.container import ServiceContainer

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = get_logger(__name__)


async def worker_startup(ctx: dict) -> None:
    """Initialize shared resources when an ARQ worker starts."""
    settings = get_settings()
    init_db(settings)
    init_redis(settings)
    ctx["settings"] = settings
    ctx["redis"] = get_redis_client()
    ctx["worker_id"] = uuid4().hex

    from app.collectors.reddit import register_reddit_collector
    from app.collectors.rss import register_rss_collector

    register_reddit_collector(redis=ctx["redis"])
    register_rss_collector(redis=ctx["redis"])
    logger.info("ARQ worker started", extra={"worker_id": ctx["worker_id"]})


async def worker_shutdown(ctx: dict) -> None:
    """Release resources when an ARQ worker stops."""
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
