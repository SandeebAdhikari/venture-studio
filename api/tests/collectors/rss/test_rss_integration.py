"""Integration tests for RSS collector through collection pipeline."""

from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.collection.collectors.registry import clear_collectors, register_collector
from app.collection.service import ComplaintCollectionService
from app.collectors.rss.collector import RssRateLimiter
from app.collectors.rss.models import RssCollectorSettings
from app.collectors.rss.service import RssCollectorService
from app.db.enums import RssFeedCategory, SourceType
from app.db.models.rss_feed import RssFeed
from app.db.models.source import Source
from app.repositories import get_repositories
from tests.collectors.rss.fixtures import sample_rss_xml


@pytest.fixture(autouse=True)
def _reset_registry():
    clear_collectors()
    yield
    clear_collectors()


@pytest.fixture
async def rss_source_with_feed(db_session: AsyncSession) -> Source:
    source = Source(
        name=f"rss-industry-{uuid4()}",
        source_type=SourceType.RSS.value,
        config={
            "url": "https://example.com/feed.xml",
            "category": RssFeedCategory.INDUSTRY.value,
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
        category=RssFeedCategory.INDUSTRY.value,
        enabled=True,
        polling_interval_sec=3600,
        entry_limit=10,
        source_id=source.id,
    )
    db_session.add(feed)
    await db_session.flush()
    source.config = {**source.config, "feed_id": str(feed.id), "feed_name": feed.name}
    await db_session.flush()
    return source


@pytest.mark.asyncio
async def test_collect_enabled_sources_ingests_rss_items(
    db_session: AsyncSession,
    rss_source_with_feed: Source,
):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sample_rss_xml().encode("utf-8"))

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
        register_collector(SourceType.RSS.value, service)

        collection = ComplaintCollectionService(get_repositories(db_session))
        result = await collection.collect_enabled_sources()

    assert result.sources_processed == 1
    assert result.inserted >= 1
    assert result.items[0].status == "completed"
    assert result.items[0].inserted >= 1


@pytest.mark.asyncio
async def test_collect_enabled_sources_deduplicates_on_second_run(
    db_session: AsyncSession,
    rss_source_with_feed: Source,
):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sample_rss_xml().encode("utf-8"))

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
        register_collector(SourceType.RSS.value, service)

        collection = ComplaintCollectionService(get_repositories(db_session))
        first = await collection.collect_enabled_sources()
        second = await collection.collect_enabled_sources()

    assert first.inserted >= 1
    assert second.items[0].status == "completed"
    assert second.items[0].duplicates >= 1
