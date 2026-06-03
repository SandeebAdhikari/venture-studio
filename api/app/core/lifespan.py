"""Application lifespan — startup and shutdown hooks."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

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

    yield

    logger.info("Shutting down application")
    await close_redis()
    await close_db()
