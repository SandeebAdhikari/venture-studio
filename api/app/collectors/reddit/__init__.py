"""Reddit collector registration and exports."""

from __future__ import annotations

from app.collection.collectors.registry import register_collector
from app.collectors.reddit.service import RedditCollectorService
from app.db.enums import SourceType
from app.logging import get_logger

logger = get_logger(__name__)


def register_reddit_collector(*, redis=None) -> RedditCollectorService:
    """Register the Reddit collector with the global source collector registry."""
    if redis is None:
        try:
            from app.redis.client import get_redis_client

            redis = get_redis_client()
        except RuntimeError:
            redis = None

    service = RedditCollectorService(redis=redis)
    register_collector(SourceType.REDDIT.value, service)
    logger.info("Reddit collector registered")
    return service


__all__ = [
    "RedditCollectorService",
    "register_reddit_collector",
]
