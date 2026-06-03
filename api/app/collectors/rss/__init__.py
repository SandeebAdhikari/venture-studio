"""RSS collector registration and exports."""

from __future__ import annotations

from app.collection.collectors.registry import register_collector
from app.collectors.rss.service import RssCollectorService
from app.db.enums import SourceType
from app.logging import get_logger

logger = get_logger(__name__)


def register_rss_collector(*, redis=None) -> RssCollectorService:
    """Register the RSS collector with the global source collector registry."""
    if redis is None:
        try:
            from app.redis.client import get_redis_client

            redis = get_redis_client()
        except RuntimeError:
            redis = None

    service = RssCollectorService(redis=redis)
    register_collector(SourceType.RSS.value, service)
    logger.info("RSS collector registered")
    return service


__all__ = [
    "RssCollectorService",
    "register_rss_collector",
]
