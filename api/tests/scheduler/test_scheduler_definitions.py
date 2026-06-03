"""Tests that scheduler definitions use the pipeline orchestrator."""

from app.pipeline.constants import PIPELINE_STAGE_ORDER
from app.scheduler.definitions import (
    DEFAULT_SCHEDULER_JOBS,
    PIPELINE_ARQ_JOB,
    SCHEDULER_JOB_MAP,
)


def test_single_orchestrated_nightly_job() -> None:
    assert len(DEFAULT_SCHEDULER_JOBS) == 1
    job = DEFAULT_SCHEDULER_JOBS[0]
    assert job.job_name == "nightly_pipeline"
    assert job.is_orchestrated is True
    assert job.arq_jobs == (PIPELINE_ARQ_JOB,)


def test_nightly_pipeline_schedule() -> None:
    job = SCHEDULER_JOB_MAP["nightly_pipeline"]
    assert job.schedule_hour == 2
    assert job.schedule_minute == 0


def test_orchestrated_job_covers_full_pipeline_stage_count() -> None:
    """run_pipeline executes PIPELINE_STAGE_ORDER (14 stages)."""
    assert len(PIPELINE_STAGE_ORDER) == 14
