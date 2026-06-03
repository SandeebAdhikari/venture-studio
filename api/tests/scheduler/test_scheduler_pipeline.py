"""Tests linking scheduler execution to the pipeline orchestrator."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.enums import PipelineRunStatus, PipelineStage, PipelineTrigger, SchedulerTrigger
from app.pipeline.orchestrator import PipelineOrchestrator
from app.repositories import get_repositories
from app.scheduler.jobs import execute_scheduler_job
from app.schemas.pipeline import PipelineRunOptions, PipelineRunResult
from app.services.container import ServiceContainer
from app.workers.jobs import run_pipeline


@pytest.mark.asyncio
async def test_scheduler_enqueues_pipeline_with_scheduled_trigger(db_session: AsyncSession):
    repos = get_repositories(db_session)
    await repos.scheduler_jobs.ensure_defaults()

    captured: dict = {}

    class CapturingEnqueuer:
        async def enqueue_pipeline(self, **kwargs):
            captured.update(kwargs)
            from app.workers.schemas import JobEnqueueResult, JobStatus

            return JobEnqueueResult(
                job_id="job-test-1",
                job_name="run_pipeline",
                status=JobStatus.QUEUED,
            )

    await execute_scheduler_job(
        "nightly_pipeline",
        trigger=SchedulerTrigger.MANUAL,
        repos=repos,
        enqueuer=CapturingEnqueuer(),  # type: ignore[arg-type]
    )

    assert captured["trigger"] == PipelineTrigger.SCHEDULED
    assert captured["idempotency_key"].startswith("scheduler:nightly_pipeline:")


@pytest.mark.asyncio
async def test_run_pipeline_worker_invokes_orchestrator(db_session: AsyncSession, monkeypatch):
    settings = Settings(api_key="test-scheduler-pipeline-key")
    from app.db.session import init_db
    from app.redis.client import get_redis_client, init_redis

    init_db(settings)
    init_redis(settings)

    expected = PipelineRunResult(
        pipeline_run_id=uuid4(),
        status=PipelineRunStatus.COMPLETED,
        stages_completed=14,
        stages_failed=0,
        stages_skipped=0,
        duration_ms=100,
    )

    async def mock_run_pipeline(self, *, trigger=PipelineTrigger.API, options=None):
        assert trigger == PipelineTrigger.SCHEDULED
        return expected

    monkeypatch.setattr(PipelineOrchestrator, "run_pipeline", mock_run_pipeline)

    ctx = {
        "job_id": f"test-{uuid4()}",
        "job_try": 1,
        "max_tries": 3,
        "redis": get_redis_client(),
        "worker_id": "test-worker",
        "settings": settings,
    }

    try:
        result = await run_pipeline(
            ctx,
            trigger=PipelineTrigger.SCHEDULED.value,
            options=PipelineRunOptions().model_dump(mode="json"),
        )
        assert result["status"] == "completed"
        assert result["stages_completed"] == 14
    finally:
        redis = get_redis_client()
        await redis.delete(f"job:status:{ctx['job_id']}")
        await redis.zrem("jobs:recent", ctx["job_id"])


@pytest.mark.asyncio
async def test_orchestrator_records_metrics_on_scheduled_run(db_session: AsyncSession, monkeypatch):
    from app.collection.collectors.registry import clear_collectors, register_collector
    from app.collection.schemas import RawComplaintInput
    from app.db.enums import SourceType
    from app.db.models.source import Source

    clear_collectors()
    metrics_calls: list[str] = []

    class _StaticCollector:
        async def fetch(self, _source):
            return [
                RawComplaintInput(
                    external_id=f"ext-{uuid4()}",
                    url=f"https://example.com/{uuid4()}",
                    title="Pricing pain",
                    body="Too expensive for our team workflow needs daily.",
                )
            ]

    register_collector(SourceType.REDDIT.value, _StaticCollector())

    source = Source(
        name=f"metrics-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    settings = Settings(
        api_key="test-metrics-key",
        pipeline_max_retries=0,
        pipeline_retry_backoff_sec=0.01,
    )
    repos = get_repositories(db_session)
    orchestrator = PipelineOrchestrator(repos, ServiceContainer(repos), settings)

    from app.observability import metrics as metrics_module

    original = metrics_module._recorder.record_pipeline_run

    def tracking_record_pipeline_run(**kwargs):
        metrics_calls.append(f"pipeline:{kwargs['status']}:{kwargs['trigger']}")
        return original(**kwargs)

    monkeypatch.setattr(
        metrics_module._recorder,
        "record_pipeline_run",
        tracking_record_pipeline_run,
    )

    result = await orchestrator.run_pipeline(
        trigger=PipelineTrigger.SCHEDULED,
        options=PipelineRunOptions(stages_only=[PipelineStage.COLLECT]),
    )

    assert result.status == PipelineRunStatus.COMPLETED
    assert any("scheduled" in call for call in metrics_calls)

    clear_collectors()
