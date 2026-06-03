"""API tests for pipeline endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.collection.collectors.registry import clear_collectors, register_collector
from app.collection.schemas import RawComplaintInput
from app.db.enums import PipelineRunStatus, PipelineStage, SourceType
from app.db.models.source import Source


class _StaticCollector:
    async def fetch(self, _source) -> list[RawComplaintInput]:
        return [
            RawComplaintInput(
                external_id=f"api-ext-{uuid4()}",
                url=f"https://example.com/api/{uuid4()}",
                title="Missing export feature",
                body="There is no way to export our data from this tool. We need CSV export daily.",
            )
        ]


@pytest.fixture(autouse=True)
def _reset_collectors():
    clear_collectors()
    yield
    clear_collectors()


@pytest.fixture
async def pipeline_source(db_session: AsyncSession) -> Source:
    source = Source(
        name=f"api-pipeline-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "startups"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()
    register_collector(SourceType.REDDIT.value, _StaticCollector())
    return source


async def test_post_pipeline_run(
    client: AsyncClient,
    auth_headers: dict[str, str],
    pipeline_source: Source,
):
    response = await client.post(
        "/api/v1/pipeline/run",
        headers=auth_headers,
        json={
            "options": {
                "stages_only": ["collect"],
            }
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == PipelineRunStatus.COMPLETED.value
    assert body["stages_completed"] == 1
    run_id = body["pipeline_run_id"]

    detail_response = await client.get(
        f"/api/v1/pipeline/runs/{run_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == run_id
    assert len(detail["stage_runs"]) == 1
    assert detail["stage_runs"][0]["stage"] == PipelineStage.COLLECT.value
    assert detail["audit_trail"]


async def test_list_pipeline_runs(
    client: AsyncClient,
    auth_headers: dict[str, str],
    pipeline_source: Source,
):
    await client.post(
        "/api/v1/pipeline/run",
        headers=auth_headers,
        json={"options": {"stages_only": ["collect"]}},
    )

    response = await client.get(
        "/api/v1/pipeline/runs",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1


async def test_pipeline_run_requires_auth(client: AsyncClient):
    response = await client.post("/api/v1/pipeline/run", json={})
    assert response.status_code == 401
