"""API tests for dashboard endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.collection.collectors.registry import clear_collectors, register_collector
from app.collection.schemas import RawComplaintInput
from app.db.enums import PipelineStage, SourceType
from app.db.models.source import Source


class _StaticCollector:
    async def fetch(self, _source) -> list[RawComplaintInput]:
        return [
            RawComplaintInput(
                external_id=f"dash-ext-{uuid4()}",
                url=f"https://example.com/dash/{uuid4()}",
                title="Dashboard export pain",
                body="We cannot export analytics and it blocks our weekly reporting workflow.",
            )
        ]


@pytest.fixture(autouse=True)
def _reset_collectors():
    clear_collectors()
    yield
    clear_collectors()


@pytest.fixture
async def dashboard_source(db_session: AsyncSession) -> Source:
    source = Source(
        name=f"dashboard-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "startups"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()
    register_collector(SourceType.REDDIT.value, _StaticCollector())
    return source


@pytest.mark.asyncio
async def test_dashboard_summary(
    client: AsyncClient,
    auth_headers: dict[str, str],
    dashboard_source: Source,
):
    pipeline_response = await client.post(
        "/api/v1/pipeline/run",
        headers=auth_headers,
        json={"options": {"stages_only": [PipelineStage.COLLECT.value]}},
    )
    assert pipeline_response.status_code == 201

    response = await client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "generated_at" in body
    assert body["collection"]["signals_total"] >= 1
    assert body["pipeline"]["latest"] is not None
    assert "agents" in body
    assert len(body["agents"]) == 8


@pytest.mark.asyncio
async def test_dashboard_pipeline(
    client: AsyncClient,
    auth_headers: dict[str, str],
    dashboard_source: Source,
):
    await client.post(
        "/api/v1/pipeline/run",
        headers=auth_headers,
        json={"options": {"stages_only": [PipelineStage.COLLECT.value]}},
    )

    response = await client.get(
        "/api/v1/dashboard/pipeline?include_stages=true",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["runs"]["total"] >= 1
    assert body["latest_detail"] is not None
    assert len(body["latest_detail"]["stage_runs"]) >= 1
    assert len(body["stage_order"]) == 14


@pytest.mark.asyncio
async def test_dashboard_opportunities_empty(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    response = await client.get("/api/v1/dashboard/opportunities", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["source"] in {"executive_ranking", "opportunity_score"}
    assert body["items"] == []


@pytest.mark.asyncio
async def test_dashboard_reports(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    response = await client.get("/api/v1/dashboard/reports", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "venture_reports" in body
    assert "total_by_type" in body
    assert "venture_recommendation" in body["total_by_type"]
    assert "top_opportunities" in body["total_by_type"]
