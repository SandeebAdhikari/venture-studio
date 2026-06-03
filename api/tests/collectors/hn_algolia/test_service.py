"""Tests for HN Algolia collector service behavior."""

from uuid import uuid4

import httpx
import pytest

from app.collectors.hn_algolia.collector import HnAlgoliaRateLimiter
from app.collectors.hn_algolia.models import HnAlgoliaCollectorSettings
from app.collectors.hn_algolia.service import HnAlgoliaCollectorService
from app.db.enums import SourceType
from app.db.models.source import Source
from tests.collectors.hn_algolia.test_collector import _search_response


@pytest.mark.asyncio
async def test_service_respects_min_points_filter():
    source = Source(
        name=f"hn-points-{uuid4()}",
        source_type=SourceType.HN_ALGOLIA.value,
        config={"query": "wish", "min_points": 100, "max_pages": 1},
        enabled=True,
    )

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_search_response())

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://hn.algolia.com/api/v1",
    ) as client:
        service = HnAlgoliaCollectorService(
            settings=HnAlgoliaCollectorSettings(rate_limit_interval_sec=0),
            client=client,
        )
        service._rate_limiter = HnAlgoliaRateLimiter(min_interval_sec=0)
        items = await service.fetch(source)

    assert items == []
