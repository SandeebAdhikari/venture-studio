"""Tests for background job execution and enqueue API."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.enums import SourceType
from app.db.models.source import Source
from app.pipeline.schemas import StageExecutionResult
from app.workers.enqueue import JobEnqueuer, close_arq_pool, get_arq_pool
from app.workers.jobs import collect
from app.workers.monitoring import JobMonitor
from app.workers.schemas import JobStatus


@pytest.fixture
async def job_enqueuer() -> JobEnqueuer:
    pool = await get_arq_pool(Settings(api_key="test-enqueue-key"))
    yield JobEnqueuer(pool, Settings(api_key="test-enqueue-key"))
    await close_arq_pool()


@pytest.mark.asyncio
async def test_enqueue_collect_job(job_enqueuer: JobEnqueuer):
    result = await job_enqueuer.enqueue_stage("collect")
    assert result.job_name == "collect"
    assert result.status == JobStatus.QUEUED

    record = await job_enqueuer.get_job(result.job_id)
    assert record is not None
    assert record.job_name == "collect"
    assert record.status == JobStatus.QUEUED


@pytest.mark.asyncio
async def test_collect_job_executes_with_mocked_executor(
    db_session: AsyncSession,
    monkeypatch,
):
    from app.db.session import init_db
    from app.redis.client import get_redis_client, init_redis

    settings = Settings(api_key="test-job-exec-key")
    init_db(settings)
    init_redis(settings)

    async def mock_execute(_self, _stage, _opts=None):
        return StageExecutionResult(
            items_in=1,
            items_out=1,
            records_processed=1,
            metadata={"mock": True},
        )

    from app.pipeline import executor as executor_module

    monkeypatch.setattr(executor_module.PipelineStageExecutor, "execute", mock_execute)

    ctx = {
        "job_id": f"test-{uuid4()}",
        "job_try": 1,
        "max_tries": 3,
        "redis": get_redis_client(),
        "worker_id": "test-worker",
        "settings": settings,
    }

    try:
        result = await collect(ctx, options={})
        assert result["status"] == "completed"
        assert result["items_out"] == 1

        monitor = JobMonitor(get_redis_client(), settings)
        record = await monitor.get(ctx["job_id"])
        assert record is not None
        assert record.status == JobStatus.COMPLETED
    finally:
        redis = get_redis_client()
        await redis.delete(f"job:status:{ctx['job_id']}")
        await redis.zrem("jobs:recent", ctx["job_id"])


@pytest.mark.asyncio
async def test_jobs_api_enqueue_and_get(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    response = await client.post(
        "/api/v1/jobs/collect",
        headers=auth_headers,
        json={"options": {}},
    )
    assert response.status_code == 202
    body = response.json()
    job_id = body["job_id"]

    status_response = await client.get(
        f"/api/v1/jobs/{job_id}",
        headers=auth_headers,
    )
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["job_id"] == job_id
    assert status_body["job_name"] == "collect"


@pytest.mark.asyncio
async def test_pipeline_background_run_returns_job(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    source = Source(
        name=f"bg-pipeline-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    response = await client.post(
        "/api/v1/pipeline/run?background=true",
        headers=auth_headers,
        json={"options": {"stages_only": ["collect"]}},
    )
    assert response.status_code == 202
    assert "job_id" in response.json()
