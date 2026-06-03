"""Scheduler job definitions (no repository imports)."""

from __future__ import annotations

from dataclasses import dataclass

# ARQ job enqueued for orchestrated nightly runs (PipelineOrchestrator).
PIPELINE_ARQ_JOB = "run_pipeline"

# Legacy stage job names retained for manual /api/v1/jobs/* execution only.
RESEARCH_AGENT_JOBS = (
    "market_research",
    "competitor_analysis",
    "customer_research",
    "revenue_validation",
    "product_strategy",
    "go_to_market",
    "growth_strategy",
    "human_proxy",
)


@dataclass(frozen=True)
class SchedulerJobDefinition:
    job_name: str
    display_name: str
    description: str
    schedule_hour: int
    schedule_minute: int
    arq_jobs: tuple[str, ...]

    @property
    def is_orchestrated(self) -> bool:
        return self.arq_jobs == (PIPELINE_ARQ_JOB,)


DEFAULT_SCHEDULER_JOBS: tuple[SchedulerJobDefinition, ...] = (
    SchedulerJobDefinition(
        job_name="nightly_pipeline",
        display_name="Nightly Venture Pipeline",
        description=(
            "Run the full Venture Studio lifecycle via the pipeline orchestrator "
            "(collect through venture report)"
        ),
        schedule_hour=2,
        schedule_minute=0,
        arq_jobs=(PIPELINE_ARQ_JOB,),
    ),
)

SCHEDULER_JOB_MAP: dict[str, SchedulerJobDefinition] = {
    job.job_name: job for job in DEFAULT_SCHEDULER_JOBS
}


def get_job_definition(job_name: str) -> SchedulerJobDefinition | None:
    return SCHEDULER_JOB_MAP.get(job_name)
