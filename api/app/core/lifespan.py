"""Application lifespan — startup and shutdown hooks."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.db.session import close_db, init_db
from app.logging import configure_logging, get_logger
from app.redis.client import close_redis, init_redis

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage resource initialization and teardown."""
    settings: Settings = get_settings()

    configure_logging(settings)
    logger.info(
        "Starting application",
        extra={"environment": settings.environment, "debug": settings.debug},
    )

    init_db(settings)
    init_redis(settings)

    from app.collectors.reddit import register_reddit_collector
    from app.collectors.rss import register_rss_collector

    register_reddit_collector()
    register_rss_collector()

    from app.scheduler.scheduler import start_scheduler

    await start_scheduler()

    yield

    logger.info("Shutting down application")
    from app.scheduler.scheduler import shutdown_scheduler

    await shutdown_scheduler()
    await close_redis()
    await close_db()
