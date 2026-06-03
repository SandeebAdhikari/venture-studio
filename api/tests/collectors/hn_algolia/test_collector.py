"""Tests for HN Algolia API collector with mocked HTTP responses."""

from uuid import uuid4

import httpx
import pytest

from app.collectors.hn_algolia.collector import HnAlgoliaApiCollector, HnAlgoliaRateLimiter
from app.collectors.hn_algolia.models import HnAlgoliaCollectorSettings, HnAlgoliaSourceConfig


def _search_response(
    *,
    hits: list[dict] | None = None,
    page: int = 0,
    nb_pages: int = 1,
) -> dict:
    if hits is None:
        hits = [
            {
                "objectID": "12345",
                "title": "Pricing is too expensive for our team",
                "story_text": "We are frustrated and wish there was an alternative.",
                "author": "founder1",
                "url": "https://example.com/post",
                "points": 42,
                "num_comments": 7,
                "created_at_i": 1_700_000_000,
                "_tags": ["story"],
            },
            {
                "objectID": "67890",
                "title": "Show HN: My weekend project",
                "story_text": "Built a small demo app over the weekend.",
                "author": "builder",
                "url": "",
                "points": 10,
                "num_comments": 2,
                "created_at_i": 1_700_000_100,
                "_tags": ["story"],
            },
        ]
    return {
        "hits": hits,
        "nbHits": len(hits),
        "page": page,
        "nbPages": nb_pages,
    }


@pytest.mark.asyncio
async def test_fetch_stories_with_mock_transport():
    source_id = uuid4()
    config = HnAlgoliaSourceConfig(query="pricing alternative", max_pages=1)

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/search")
        assert request.url.params["query"] == "pricing alternative"
        assert request.url.params["tags"] == "story"
        return httpx.Response(200, json=_search_response())

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://hn.algolia.com/api/v1",
        headers={"User-Agent": "test"},
    ) as client:
        async with HnAlgoliaApiCollector(
            settings=HnAlgoliaCollectorSettings(rate_limit_interval_sec=0),
            rate_limiter=HnAlgoliaRateLimiter(min_interval_sec=0),
            client=client,
        ) as api:
            result = await api.fetch_stories(config, source_id=source_id)

    assert result.pages_fetched == 1
    assert len(result.stories) == 2
    assert result.stories[0].external_id == "hn_12345"
    assert result.stories[0].url == "https://example.com/post"
    assert result.stories[1].hn_url == "https://news.ycombinator.com/item?id=67890"


@pytest.mark.asyncio
async def test_fetch_stories_paginates_until_nb_pages():
    source_id = uuid4()
    config = HnAlgoliaSourceConfig(query="wish", hits_per_page=1, max_pages=3)
    requested_pages: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        requested_pages.append(str(page))
        hits = [
            {
                "objectID": f"page-{page}",
                "title": f"Story on page {page} with wish keyword",
                "story_text": "Someone should build this.",
                "author": "user",
                "url": "",
                "points": 5,
                "num_comments": 1,
                "created_at_i": 1_700_000_000 + page,
            }
        ]
        return httpx.Response(200, json=_search_response(hits=hits, page=page, nb_pages=2))

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://hn.algolia.com/api/v1",
    ) as client:
        async with HnAlgoliaApiCollector(
            settings=HnAlgoliaCollectorSettings(rate_limit_interval_sec=0),
            rate_limiter=HnAlgoliaRateLimiter(min_interval_sec=0),
            client=client,
        ) as api:
            result = await api.fetch_stories(config, source_id=source_id)

    assert requested_pages == ["0", "1"]
    assert result.pages_fetched == 2
    assert len(result.stories) == 2


@pytest.mark.asyncio
async def test_fetch_stories_retries_on_transport_error():
    source_id = uuid4()
    config = HnAlgoliaSourceConfig(query="wish", max_pages=1)
    attempts = {"count": 0}

    async def handler(_request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.ConnectError("connection reset")
        return httpx.Response(200, json=_search_response(hits=[]))

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://hn.algolia.com/api/v1",
    ) as client:
        async with HnAlgoliaApiCollector(
            settings=HnAlgoliaCollectorSettings(
                rate_limit_interval_sec=0,
                max_retries=2,
                retry_backoff_sec=0,
            ),
            rate_limiter=HnAlgoliaRateLimiter(min_interval_sec=0),
            client=client,
        ) as api:
            result = await api.fetch_stories(config, source_id=source_id)

    assert attempts["count"] == 2
    assert result.stories == []


@pytest.mark.asyncio
async def test_fetch_stories_raises_after_max_retries():
    source_id = uuid4()
    config = HnAlgoliaSourceConfig(query="wish", max_pages=1)

    async def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection reset")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://hn.algolia.com/api/v1",
    ) as client:
        async with HnAlgoliaApiCollector(
            settings=HnAlgoliaCollectorSettings(
                rate_limit_interval_sec=0,
                max_retries=2,
                retry_backoff_sec=0,
            ),
            rate_limiter=HnAlgoliaRateLimiter(min_interval_sec=0),
            client=client,
        ) as api:
            with pytest.raises(httpx.ConnectError):
                await api.fetch_stories(config, source_id=source_id)
