"""Tests for RSS feed HTTP collector with mocked responses."""

from uuid import uuid4

import httpx
import pytest

from app.collectors.rss.collector import RssFeedCollector, RssRateLimiter
from app.collectors.rss.models import RssCollectorSettings
from tests.collectors.rss.fixtures import sample_rss_xml


@pytest.mark.asyncio
async def test_fetch_entries_parses_rss_feed():
    source_id = uuid4()
    feed_url = "https://example.com/feed.xml"

    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == feed_url
        return httpx.Response(200, content=sample_rss_xml().encode("utf-8"))

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, headers={"User-Agent": "test"}) as client:
        async with RssFeedCollector(
            settings=RssCollectorSettings(rate_limit_interval_sec=0, max_retries=1),
            rate_limiter=RssRateLimiter(min_interval_sec=0),
            client=client,
        ) as collector:
            entries = await collector.fetch_entries(
                feed_url,
                entry_limit=10,
                source_id=source_id,
            )

    assert len(entries) == 2
    assert entries[0].external_id == "article-1"
    assert entries[0].feed_title == "Business Signals"
    assert entries[1].url == "https://example.com/article/2"
