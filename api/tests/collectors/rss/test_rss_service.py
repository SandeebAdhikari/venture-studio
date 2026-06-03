"""Tests for RSS collector service behavior."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.rss.collector import RssRateLimiter
from app.collectors.rss.models import RssCollectorSettings
from app.collectors.rss.service import RssCollectorService
from app.db.enums import RssFeedCategory, SourceType
from app.db.models.rss_feed import RssFeed
from app.db.models.source import Source
from tests.collectors.rss.fixtures import sample_rss_xml


@pytest.fixture
async def rss_source_with_feed(db_session: AsyncSession) -> tuple[Source, RssFeed]:
    source = Source(
        name=f"rss-business-{uuid4()}",
        source_type=SourceType.RSS.value,
        config={
            "url": "https://example.com/feed.xml",
            "category": RssFeedCategory.BUSINESS.value,
            "limit": 10,
            "polling_interval_sec": 3600,
        },
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    feed = RssFeed(
        name=source.name,
        feed_url="https://example.com/feed.xml",
        category=RssFeedCategory.BUSINESS.value,
        enabled=True,
        polling_interval_sec=3600,
        entry_limit=10,
        source_id=source.id,
    )
    db_session.add(feed)
    await db_session.flush()
    return source, feed


@pytest.mark.asyncio
async def test_fetch_skips_when_polling_interval_not_elapsed(
    db_session: AsyncSession,
    rss_source_with_feed: tuple[Source, RssFeed],
):
    source, feed = rss_source_with_feed
    source.last_collected_at = datetime.now(UTC) - timedelta(minutes=5)
    await db_session.flush()

    service = RssCollectorService(
        settings=RssCollectorSettings(force_poll=False, rate_limit_interval_sec=0),
    )
    items = await service.fetch(source)
    assert items == []


@pytest.mark.asyncio
async def test_fetch_deduplicates_entries_within_batch(
    db_session: AsyncSession,
    rss_source_with_feed: tuple[Source, RssFeed],
):
    source, _feed = rss_source_with_feed

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sample_rss_xml(duplicate_guid=True).encode("utf-8"))

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, headers={"User-Agent": "test"}) as client:
        service = RssCollectorService(
            settings=RssCollectorSettings(
                force_poll=True,
                rate_limit_interval_sec=0,
                max_retries=1,
            ),
            client=client,
        )
        service._rate_limiter = RssRateLimiter(min_interval_sec=0)
        items = await service.fetch(source)

    external_ids = [item.external_id for item in items]
    assert external_ids.count("article-1") == 1
    assert len(items) == 2
    assert items[0].metadata["rss"]["collector"] == "rss"
    assert items[0].metadata["rss"]["feed_category"] == RssFeedCategory.BUSINESS.value
