"""HN Algolia collector service — maps search hits to collection pipeline inputs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from app.collection.schemas import RawComplaintInput
from app.collectors.hn_algolia.collector import HnAlgoliaApiCollector, HnAlgoliaRateLimiter
from app.collectors.hn_algolia.models import (
    HnAlgoliaCollectionStats,
    HnAlgoliaCollectorSettings,
    HnAlgoliaFetchStats,
    HnAlgoliaSourceConfig,
    HnAlgoliaStory,
)
from app.collectors.reddit.service import KeywordFilter
from app.db.models.source import Source
from app.logging import get_logger

logger = get_logger(__name__)


class HnAlgoliaCollectorService:
    """Collects Hacker News stories via Algolia search for signal ingestion."""

    def __init__(
        self,
        *,
        settings: HnAlgoliaCollectorSettings | None = None,
        redis=None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or HnAlgoliaCollectorSettings()
        self._redis = redis
        self._client = client
        self._rate_limiter = HnAlgoliaRateLimiter(
            redis=redis,
            min_interval_sec=self._settings.rate_limit_interval_sec,
        )

    async def fetch(self, source: Source) -> list[RawComplaintInput]:
        config = HnAlgoliaSourceConfig.model_validate(source.config or {})
        stats = HnAlgoliaCollectionStats()
        fetch_stats = HnAlgoliaFetchStats()
        seen_external_ids: set[str] = set()
        items: list[RawComplaintInput] = []

        keyword_filter = KeywordFilter(
            config.resolved_keywords(),
            min_matches=config.min_keyword_matches,
        )

        async with HnAlgoliaApiCollector(
            settings=self._settings,
            rate_limiter=self._rate_limiter,
            client=self._client,
        ) as api:
            search_result = await api.fetch_stories(config, source_id=source.id)
            stories = search_result.stories
            fetch_stats.hits_fetched = len(stories)
            fetch_stats.pages_fetched = search_result.pages_fetched

        for story in stories:
            stats.total_candidates += 1
            item = self._story_to_raw(
                story,
                source_id=source.id,
                source_name=source.name,
                config=config,
                stats=fetch_stats,
                seen_external_ids=seen_external_ids,
                keyword_filter=keyword_filter,
            )
            if item is not None:
                items.append(item)

        stats.fetch_stats = fetch_stats
        stats.total_returned = len(items)
        logger.info(
            "HN Algolia collection complete",
            extra={
                "source_id": str(source.id),
                "source_name": source.name,
                "query": config.query,
                "hits_fetched": fetch_stats.hits_fetched,
                "total_returned": stats.total_returned,
                "duplicates_skipped": fetch_stats.duplicates_skipped,
                "keyword_filtered": fetch_stats.keyword_filtered,
                "points_filtered": fetch_stats.points_filtered,
            },
        )
        return items

    def _story_to_raw(
        self,
        story: HnAlgoliaStory,
        *,
        source_id: UUID,
        source_name: str,
        config: HnAlgoliaSourceConfig,
        stats: HnAlgoliaFetchStats,
        seen_external_ids: set[str],
        keyword_filter: KeywordFilter,
    ) -> RawComplaintInput | None:
        if story.points < config.min_points:
            stats.points_filtered += 1
            return None

        matched = keyword_filter.matched_keywords(story.title, story.body)
        if not matched:
            stats.keyword_filtered += 1
            return None

        if story.external_id in seen_external_ids:
            stats.duplicates_skipped += 1
            return None
        seen_external_ids.add(story.external_id)
        stats.keyword_matches += 1

        return RawComplaintInput(
            external_id=story.external_id,
            url=story.url,
            title=story.title,
            body=story.body,
            author=story.author,
            published_at=story.published_at,
            metadata=self._build_metadata(
                story=story,
                source_id=source_id,
                source_name=source_name,
                config=config,
                matched_keywords=matched,
            ),
        )

    def _build_metadata(
        self,
        *,
        story: HnAlgoliaStory,
        source_id: UUID,
        source_name: str,
        config: HnAlgoliaSourceConfig,
        matched_keywords: list[str],
    ) -> dict[str, Any]:
        attribution = {
            "collector": "hn_algolia",
            "collector_version": self._settings.collector_version,
            "source_id": str(source_id),
            "source_name": source_name,
            "object_id": story.object_id,
            "hn_url": story.hn_url,
            "query": config.query,
            "tags": config.tags,
            "points": story.points,
            "num_comments": story.num_comments,
            "matched_keywords": matched_keywords,
        }
        return {
            "hn_algolia": attribution,
            "score": story.points,
        }
