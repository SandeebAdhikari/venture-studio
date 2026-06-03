"""Tests for scheduler job execution."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.enums import PipelineTrigger, SchedulerRunStatus, SchedulerTrigger
from app.repositories import get_repositories
from app.scheduler.jobs import execute_scheduler_job
from app.workers.enqueue import JobEnqueuer, close_arq_pool, get_arq_pool


@pytest.fixture
async def job_enqueuer() -> JobEnqueuer:
    settings = Settings(api_key="test-scheduler-key")
    pool = await get_arq_pool(settings)
    yield JobEnqueuer(pool, settings)
    await close_arq_pool()


@pytest.mark.asyncio
async def test_execute_nightly_pipeline_enqueues_orchestrator(
    db_session: AsyncSession,
    job_enqueuer: JobEnqueuer,
):
    repos = get_repositories(db_session)
    await repos.scheduler_jobs.ensure_defaults()

    run_id = await execute_scheduler_job(
        "nightly_pipeline",
        trigger=SchedulerTrigger.MANUAL,
        repos=repos,
        enqueuer=job_enqueuer,
    )

    run = await repos.scheduler_runs.get_by_id(run_id)
    assert run is not None
    assert run.status == SchedulerRunStatus.COMPLETED.value
    assert len(run.arq_job_ids) == 1
    assert run.metadata_.get("execution_mode") == "orchestrator"
    assert run.metadata_.get("pipeline_trigger") == PipelineTrigger.SCHEDULED.value

    record = await job_enqueuer.get_job(run.arq_job_ids[0])
    assert record is not None
    assert record.job_name == "run_pipeline"


@pytest.mark.asyncio
async def test_execute_scheduler_job_records_failure(
    db_session: AsyncSession,
):
    repos = get_repositories(db_session)
    await repos.scheduler_jobs.ensure_defaults()

    class FailingEnqueuer:
        async def enqueue_pipeline(self, **_kwargs):
            raise RuntimeError("enqueue failed")

    with pytest.raises(RuntimeError, match="enqueue failed"):
        await execute_scheduler_job(
            "nightly_pipeline",
            trigger=SchedulerTrigger.MANUAL,
            repos=repos,
            enqueuer=FailingEnqueuer(),  # type: ignore[arg-type]
        )

    run = await repos.scheduler_runs.get_latest_for_job("nightly_pipeline")
    assert run is not None
    assert run.status == SchedulerRunStatus.FAILED.value
    assert "enqueue failed" in (run.error or "")


@pytest.mark.asyncio
async def test_scheduled_run_skips_disabled_job(
    db_session: AsyncSession, job_enqueuer: JobEnqueuer
):
    repos = get_repositories(db_session)
    await repos.scheduler_jobs.ensure_defaults()
    job = await repos.scheduler_jobs.get_by_name("nightly_pipeline")
    assert job is not None
    await repos.scheduler_jobs.set_enabled(job, False)

    with pytest.raises(RuntimeError, match="disabled"):
        await execute_scheduler_job(
            "nightly_pipeline",
            trigger=SchedulerTrigger.SCHEDULED,
            repos=repos,
            enqueuer=job_enqueuer,
        )


@pytest.mark.asyncio
async def test_ensure_defaults_disables_legacy_stage_jobs(db_session: AsyncSession):
    repos = get_repositories(db_session)
    from app.scheduler.definitions import SchedulerJobDefinition

    legacy_job = await repos.scheduler_jobs.get_by_name("collect")
    if legacy_job is None:
        legacy = SchedulerJobDefinition(
            job_name="collect",
            display_name="Collect",
            description="legacy",
            schedule_hour=2,
            schedule_minute=0,
            arq_jobs=("collect",),
        )
        legacy_job = await repos.scheduler_jobs.create_from_definition(legacy)
    else:
        await repos.scheduler_jobs.set_enabled(legacy_job, True)

    await repos.scheduler_jobs.ensure_defaults()

    legacy_job = await repos.scheduler_jobs.get_by_name("collect")
    assert legacy_job is not None
    assert legacy_job.enabled is False

    nightly = await repos.scheduler_jobs.get_by_name("nightly_pipeline")
    assert nightly is not None
    assert nightly.enabled is True
