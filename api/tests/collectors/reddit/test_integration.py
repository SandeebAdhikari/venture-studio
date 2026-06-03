"""Integration tests for Reddit collector through collection pipeline."""

from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.collection.collectors.registry import clear_collectors, register_collector
from app.collection.service import ComplaintCollectionService
from app.collectors.reddit.collector import RedditRateLimiter
from app.collectors.reddit.models import RedditCollectorSettings
from app.collectors.reddit.service import RedditCollectorService
from app.db.enums import SourceType
from app.db.models.source import Source
from app.repositories import get_repositories
from tests.collectors.reddit.test_collector import _comment_listing, _post_listing


@pytest.fixture(autouse=True)
def _reset_registry():
    clear_collectors()
    yield
    clear_collectors()


@pytest.fixture
async def reddit_source(db_session: AsyncSession) -> Source:
    source = Source(
        name=f"reddit-saas-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS", "limit": 10, "include_comments": True},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()
    return source


@pytest.mark.asyncio
async def test_reddit_collector_fetch_applies_keyword_filter_and_deduplication(
    reddit_source: Source,
):
    seen_paths: set[str] = set()

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.add(request.url.path)
        if request.url.path.endswith("/SaaS/new.json"):
            listing = _post_listing("SaaS")
            duplicate = listing["data"]["children"][0].copy()
            listing["data"]["children"].append(duplicate)
            return httpx.Response(200, json=listing)
        if "/comments/abc123.json" in request.url.path:
            return httpx.Response(200, json=_comment_listing("SaaS"))
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://www.reddit.com",
        headers={"User-Agent": "test"},
    ) as client:
        service = RedditCollectorService(
            settings=RedditCollectorSettings(rate_limit_interval_sec=0),
            client=client,
        )
        service._rate_limiter = RedditRateLimiter(min_interval_sec=0)
        items = await service.fetch(reddit_source)

    external_ids = [item.external_id for item in items]
    assert "t3_abc123" in external_ids
    assert "t1_cmt1" in external_ids
    assert external_ids.count("t3_abc123") == 1
    assert all(item.metadata["reddit"]["collector"] == "reddit" for item in items)
    assert not any(item.external_id == "t3_neutral1" for item in items)


@pytest.mark.asyncio
async def test_collect_enabled_sources_ingests_reddit_items(
    db_session: AsyncSession,
    reddit_source: Source,
):
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/SaaS/new.json"):
            return httpx.Response(200, json=_post_listing("SaaS"))
        if "/comments/abc123.json" in request.url.path:
            return httpx.Response(200, json=_comment_listing("SaaS"))
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://www.reddit.com",
        headers={"User-Agent": "test"},
    ) as client:
        service = RedditCollectorService(
            settings=RedditCollectorSettings(rate_limit_interval_sec=0),
            client=client,
        )
        service._rate_limiter = RedditRateLimiter(min_interval_sec=0)
        register_collector(SourceType.REDDIT.value, service)

        collection = ComplaintCollectionService(get_repositories(db_session))
        result = await collection.collect_enabled_sources()

    assert result.sources_processed == 1
    assert result.inserted >= 1
    assert result.items[0].status == "completed"
