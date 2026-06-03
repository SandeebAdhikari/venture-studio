"""Hacker News Algolia collector registration and exports."""

from __future__ import annotations

from app.collection.collectors.registry import register_collector
from app.collectors.hn_algolia.service import HnAlgoliaCollectorService
from app.db.enums import SourceType
from app.logging import get_logger

logger = get_logger(__name__)


def register_hn_algolia_collector(*, redis=None) -> HnAlgoliaCollectorService:
    """Register the HN Algolia collector with the global source collector registry."""
    if redis is None:
        try:
            from app.redis.client import get_redis_client

            redis = get_redis_client()
        except RuntimeError:
            redis = None

    service = HnAlgoliaCollectorService(redis=redis)
    register_collector(SourceType.HN_ALGOLIA.value, service)
    logger.info("HN Algolia collector registered")
    return service


__all__ = [
    "HnAlgoliaCollectorService",
    "register_hn_algolia_collector",
]
