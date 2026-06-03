"""Tests that nightly scheduler order aligns with the pipeline."""

from app.db.enums import PipelineStage
from app.pipeline.constants import PIPELINE_STAGE_ORDER
from app.scheduler.definitions import DEFAULT_SCHEDULER_JOBS
from app.workers.jobs import STAGE_JOB_MAP


def _scheduled_arq_jobs_in_cron_order() -> list[str]:
    jobs = sorted(
        DEFAULT_SCHEDULER_JOBS,
        key=lambda job: (job.schedule_hour, job.schedule_minute, job.job_name),
    )
    arq_jobs: list[str] = []
    for job in jobs:
        arq_jobs.extend(job.arq_jobs)
    return arq_jobs


def test_nightly_schedule_order_matches_pipeline_order() -> None:
    scheduled_stages = [
        STAGE_JOB_MAP[job_name]
        for job_name in _scheduled_arq_jobs_in_cron_order()
    ]

    assert scheduled_stages == list(PIPELINE_STAGE_ORDER)


def test_score_runs_before_research_agents() -> None:
    arq_jobs = _scheduled_arq_jobs_in_cron_order()
    score_index = arq_jobs.index("score")
    research_index = arq_jobs.index("market_research")

    assert score_index < research_index
    assert STAGE_JOB_MAP["score"] == PipelineStage.SCORE_OPPORTUNITIES
