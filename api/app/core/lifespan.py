"""Application lifespan — startup and shutdown hooks."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.db.session import close_db, init_db
from app.logging import configure_logging, get_logger
from app.observability.setup import init_observability
from app.redis.client import close_redis, init_redis

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage resource initialization and teardown."""
    settings: Settings = get_settings()

    configure_logging(settings)
    init_observability(settings)
    logger.info(
        "Starting application",
        extra={"environment": settings.environment, "debug": settings.debug},
    )

    init_db(settings)
    init_redis(settings)

    from app.db.session import get_session_factory
    from app.observability.alerting.engine import init_alerting
    from app.observability.alerting.monitor import start_alert_monitor, stop_alert_monitor
    from app.observability.alerting.validation import validate_alert_config
    from app.redis.client import get_redis_client

    alert_validation = validate_alert_config(settings)
    for warning in alert_validation.warnings:
        logger.warning("Alert config: %s", warning)
    for error in alert_validation.errors:
        logger.error("Alert config: %s", error)
    if settings.alert_validation_strict and alert_validation.errors:
        raise RuntimeError("; ".join(alert_validation.errors))

    init_alerting(settings, redis=get_redis_client())
    start_alert_monitor(get_redis_client(), get_session_factory(), settings)

    from app.collectors.hn_algolia import register_hn_algolia_collector
    from app.collectors.reddit import register_reddit_collector
    from app.collectors.rss import register_rss_collector

    register_reddit_collector()
    register_rss_collector()
    register_hn_algolia_collector()

    from app.scheduler.scheduler import start_scheduler

    await start_scheduler()

    yield

    logger.info("Shutting down application")
    await stop_alert_monitor()
    from app.scheduler.scheduler import shutdown_scheduler

    await shutdown_scheduler()
    await close_redis()
    await close_db()
