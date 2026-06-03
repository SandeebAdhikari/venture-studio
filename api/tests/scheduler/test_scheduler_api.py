"""API tests for scheduler endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import get_repositories


@pytest.fixture
async def seeded_scheduler_jobs(db_session: AsyncSession):
    repos = get_repositories(db_session)
    await repos.scheduler_jobs.ensure_defaults()
    await db_session.flush()
    return repos


@pytest.mark.asyncio
async def test_list_scheduler_jobs(
    client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_scheduler_jobs,
):
    response = await client.get("/api/v1/scheduler/jobs", headers=auth_headers)
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 7
    names = {job["job_name"] for job in jobs}
    assert names == {
        "collect",
        "classify",
        "generate_opportunities",
        "score",
        "research_agents",
        "executive_ranking",
        "venture_report",
    }
    collect = next(job for job in jobs if job["job_name"] == "collect")
    assert collect["schedule_hour"] == 2
    assert collect["enabled"] is True
    assert collect["schedule_cron"] == "0 2 * * *"


@pytest.mark.asyncio
async def test_manual_trigger_scheduler_job(
    client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_scheduler_jobs,
    db_session: AsyncSession,
):
    response = await client.post("/api/v1/scheduler/run/collect", headers=auth_headers)
    assert response.status_code == 202
    body = response.json()
    assert body["job_name"] == "collect"
    assert body["status"] == "completed"
    assert len(body["arq_job_ids"]) == 1

    list_response = await client.get("/api/v1/scheduler/jobs", headers=auth_headers)
    collect = next(job for job in list_response.json() if job["job_name"] == "collect")
    assert collect["last_run"] is not None
    assert collect["last_run"]["trigger"] == "manual"


@pytest.mark.asyncio
async def test_disable_scheduler_job(
    client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_scheduler_jobs,
):
    disable = await client.patch(
        "/api/v1/scheduler/jobs/collect",
        headers=auth_headers,
        json={"enabled": False},
    )
    assert disable.status_code == 200
    assert disable.json()["enabled"] is False

    blocked = await client.post("/api/v1/scheduler/run/collect", headers=auth_headers)
    assert blocked.status_code == 422

    enable = await client.patch(
        "/api/v1/scheduler/jobs/collect",
        headers=auth_headers,
        json={"enabled": True},
    )
    assert enable.status_code == 200
    assert enable.json()["enabled"] is True


@pytest.mark.asyncio
async def test_unknown_scheduler_job_returns_422(
    client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_scheduler_jobs,
):
    response = await client.post("/api/v1/scheduler/run/not-a-job", headers=auth_headers)
    assert response.status_code == 422
