"""Tests for scheduler job execution."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.enums import SchedulerRunStatus, SchedulerTrigger
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
async def test_execute_scheduler_job_enqueues_arq_work(
    db_session: AsyncSession,
    job_enqueuer: JobEnqueuer,
):
    repos = get_repositories(db_session)
    await repos.scheduler_jobs.ensure_defaults()

    run_id = await execute_scheduler_job(
        "collect",
        trigger=SchedulerTrigger.MANUAL,
        repos=repos,
        enqueuer=job_enqueuer,
    )

    run = await repos.scheduler_runs.get_by_id(run_id)
    assert run is not None
    assert run.status == SchedulerRunStatus.COMPLETED.value
    assert len(run.arq_job_ids) == 1

    record = await job_enqueuer.get_job(run.arq_job_ids[0])
    assert record is not None
    assert record.job_name == "collect"


@pytest.mark.asyncio
async def test_execute_research_agents_enqueues_all_agent_jobs(
    db_session: AsyncSession,
    job_enqueuer: JobEnqueuer,
):
    repos = get_repositories(db_session)
    await repos.scheduler_jobs.ensure_defaults()

    run_id = await execute_scheduler_job(
        "research_agents",
        trigger=SchedulerTrigger.MANUAL,
        repos=repos,
        enqueuer=job_enqueuer,
    )

    run = await repos.scheduler_runs.get_by_id(run_id)
    assert run is not None
    assert run.status == SchedulerRunStatus.COMPLETED.value
    assert len(run.arq_job_ids) == 8


@pytest.mark.asyncio
async def test_execute_scheduler_job_records_failure(
    db_session: AsyncSession,
):
    repos = get_repositories(db_session)
    await repos.scheduler_jobs.ensure_defaults()

    class FailingEnqueuer:
        async def enqueue_stage(self, *_args, **_kwargs):
            raise RuntimeError("enqueue failed")

    with pytest.raises(RuntimeError, match="enqueue failed"):
        await execute_scheduler_job(
            "classify",
            trigger=SchedulerTrigger.MANUAL,
            repos=repos,
            enqueuer=FailingEnqueuer(),  # type: ignore[arg-type]
        )

    run = await repos.scheduler_runs.get_latest_for_job("classify")
    assert run is not None
    assert run.status == SchedulerRunStatus.FAILED.value
    assert "enqueue failed" in (run.error or "")


@pytest.mark.asyncio
async def test_scheduled_run_skips_disabled_job(db_session: AsyncSession, job_enqueuer: JobEnqueuer):
    repos = get_repositories(db_session)
    await repos.scheduler_jobs.ensure_defaults()
    job = await repos.scheduler_jobs.get_by_name("collect")
    assert job is not None
    await repos.scheduler_jobs.set_enabled(job, False)

    with pytest.raises(RuntimeError, match="disabled"):
        await execute_scheduler_job(
            "collect",
            trigger=SchedulerTrigger.SCHEDULED,
            repos=repos,
            enqueuer=job_enqueuer,
        )
