"""Integration tests for HN Algolia collector through collection pipeline."""

from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.collection.collectors.registry import clear_collectors, register_collector
from app.collection.service import ComplaintCollectionService
from app.collectors.hn_algolia.collector import HnAlgoliaRateLimiter
from app.collectors.hn_algolia.models import HnAlgoliaCollectorSettings
from app.collectors.hn_algolia.service import HnAlgoliaCollectorService
from app.db.enums import SourceType
from app.db.models.source import Source
from app.repositories import get_repositories
from tests.collectors.hn_algolia.test_collector import _search_response


@pytest.fixture(autouse=True)
def _reset_registry():
    clear_collectors()
    yield
    clear_collectors()


@pytest.fixture
async def hn_source(db_session: AsyncSession) -> Source:
    source = Source(
        name=f"hn-wish-{uuid4()}",
        source_type=SourceType.HN_ALGOLIA.value,
        config={"query": "wish alternative", "max_pages": 1},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()
    return source


@pytest.mark.asyncio
async def test_hn_collector_fetch_applies_keyword_filter_and_deduplication(hn_source: Source):
    async def handler(request: httpx.Request) -> httpx.Response:
        response = _search_response()
        duplicate = response["hits"][0].copy()
        response["hits"].append(duplicate)
        return httpx.Response(200, json=response)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://hn.algolia.com/api/v1",
        headers={"User-Agent": "test"},
    ) as client:
        service = HnAlgoliaCollectorService(
            settings=HnAlgoliaCollectorSettings(rate_limit_interval_sec=0),
            client=client,
        )
        service._rate_limiter = HnAlgoliaRateLimiter(min_interval_sec=0)
        items = await service.fetch(hn_source)

    external_ids = [item.external_id for item in items]
    assert "hn_12345" in external_ids
    assert external_ids.count("hn_12345") == 1
    assert not any(item.external_id == "hn_67890" for item in items)
    assert all(item.metadata["hn_algolia"]["collector"] == "hn_algolia" for item in items)


@pytest.mark.asyncio
async def test_collect_enabled_sources_ingests_hn_algolia_items(
    db_session: AsyncSession,
    hn_source: Source,
):
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_search_response())

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://hn.algolia.com/api/v1",
        headers={"User-Agent": "test"},
    ) as client:
        service = HnAlgoliaCollectorService(
            settings=HnAlgoliaCollectorSettings(rate_limit_interval_sec=0),
            client=client,
        )
        service._rate_limiter = HnAlgoliaRateLimiter(min_interval_sec=0)
        register_collector(SourceType.HN_ALGOLIA.value, service)

        collection = ComplaintCollectionService(get_repositories(db_session))
        result = await collection.collect_enabled_sources()

    assert result.sources_processed == 1
    assert result.inserted >= 1
    assert result.items[0].status == "completed"
