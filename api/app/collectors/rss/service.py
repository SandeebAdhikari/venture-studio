"""RSS collector service — polls feeds and maps entries to collection inputs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import httpx

from app.collection.schemas import RawComplaintInput
from app.collectors.rss.collector import RssFeedCollector, RssRateLimiter
from app.collectors.rss.models import RssCollectorSettings, RssFeedEntry, RssSourceConfig
from app.db.models.source import Source
from app.db.session import get_session_factory
from app.logging import get_logger
from app.repositories import get_repositories

logger = get_logger(__name__)


class RssCollectorService:
    """Collects business and industry signals from configured RSS feeds."""

    def __init__(
        self,
        *,
        settings: RssCollectorSettings | None = None,
        redis=None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or RssCollectorSettings()
        self._redis = redis
        self._client = client
        self._rate_limiter = RssRateLimiter(
            redis=redis,
            min_interval_sec=self._settings.rate_limit_interval_sec,
        )

    async def fetch(self, source: Source) -> list[RawComplaintInput]:
        if not source.enabled:
            return []

        try:
            config = RssSourceConfig.from_source_config(source.config)
        except Exception as exc:
            logger.warning(
                "Invalid RSS source config",
                extra={"source_id": str(source.id), "error": str(exc)},
            )
            return []

        if not self._is_due_for_poll(source.last_collected_at, config.polling_interval_sec):
            logger.info(
                "RSS feed polling skipped — interval not elapsed",
                extra={"source_id": str(source.id), "source_name": source.name},
            )
            return []

        seen_external_ids: set[str] = set()
        items: list[RawComplaintInput] = []

        try:
            async with RssFeedCollector(
                settings=self._settings,
                rate_limiter=self._rate_limiter,
                client=self._client,
            ) as api:
                entries = await api.fetch_entries(
                    config.url,
                    entry_limit=config.limit,
                    source_id=source.id,
                )

            for entry in entries:
                if entry.external_id in seen_external_ids:
                    continue
                seen_external_ids.add(entry.external_id)
                items.append(
                    self._entry_to_raw(
                        entry,
                        config=config,
                        source_id=source.id,
                        source_name=source.name,
                    )
                )

            await self._record_poll_success(source.id, config.feed_id)
            logger.info(
                "RSS feed collected",
                extra={
                    "source_id": str(source.id),
                    "entries_fetched": len(entries),
                    "entries_returned": len(items),
                },
            )
            return items
        except Exception as exc:
            await self._record_poll_error(source.id, config.feed_id, str(exc))
            raise

    async def _record_poll_success(self, source_id: UUID, feed_id: str | None) -> None:
        factory = get_session_factory()
        async with factory() as session:
            repos = get_repositories(session)
            if feed_id is not None:
                feed = await repos.rss_feeds.get_by_id(UUID(feed_id))
                if feed is not None:
                    await repos.rss_feeds.mark_polled(feed)
            await session.commit()

    async def _record_poll_error(
        self,
        source_id: UUID,
        feed_id: str | None,
        error: str,
    ) -> None:
        factory = get_session_factory()
        async with factory() as session:
            repos = get_repositories(session)
            if feed_id is not None:
                feed = await repos.rss_feeds.get_by_id(UUID(feed_id))
                if feed is not None:
                    await repos.rss_feeds.record_error(feed, error)
            await session.commit()

    def _is_due_for_poll(
        self,
        last_collected_at: datetime | None,
        polling_interval_sec: int,
    ) -> bool:
        if self._settings.force_poll:
            return True
        if last_collected_at is None:
            return True
        elapsed = (datetime.now(UTC) - last_collected_at).total_seconds()
        return elapsed >= polling_interval_sec

    def _entry_to_raw(
        self,
        entry: RssFeedEntry,
        *,
        config: RssSourceConfig,
        source_id: UUID,
        source_name: str,
    ) -> RawComplaintInput:
        feed_name = config.feed_name or source_name
        return RawComplaintInput(
            external_id=entry.external_id,
            url=entry.url,
            title=entry.title,
            body=entry.body,
            author=entry.author,
            published_at=entry.published_at,
            metadata={
                "rss": {
                    "collector": "rss",
                    "collector_version": self._settings.collector_version,
                    "feed_id": config.feed_id,
                    "feed_name": feed_name,
                    "feed_url": config.url,
                    "feed_category": config.category,
                    "source_id": str(source_id),
                    "source_name": source_name,
                    "entry_id": entry.entry_id,
                    "feed_title": entry.feed_title,
                },
                "category": config.category,
            },
        )
