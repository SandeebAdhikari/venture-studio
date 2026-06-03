"""Scheduler job definitions (no repository imports)."""

from __future__ import annotations

from dataclasses import dataclass

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


DEFAULT_SCHEDULER_JOBS: tuple[SchedulerJobDefinition, ...] = (
    SchedulerJobDefinition(
        job_name="collect",
        display_name="Collect",
        description="Collect signals from enabled sources (Reddit, RSS, etc.)",
        schedule_hour=2,
        schedule_minute=0,
        arq_jobs=("collect",),
    ),
    SchedulerJobDefinition(
        job_name="classify",
        display_name="Classify",
        description="Classify collected signals into complaint categories",
        schedule_hour=3,
        schedule_minute=0,
        arq_jobs=("classify",),
    ),
    SchedulerJobDefinition(
        job_name="generate_opportunities",
        display_name="Generate Opportunities",
        description="Generate venture opportunities from classified complaints",
        schedule_hour=4,
        schedule_minute=0,
        arq_jobs=("generate_opportunities",),
    ),
    SchedulerJobDefinition(
        job_name="research_agents",
        display_name="Research Agents",
        description=(
            "Run all research agents (market, competitor, customer, revenue, "
            "product, GTM, growth, human proxy)"
        ),
        schedule_hour=5,
        schedule_minute=0,
        arq_jobs=RESEARCH_AGENT_JOBS,
    ),
    SchedulerJobDefinition(
        job_name="executive_ranking",
        display_name="Executive Ranking",
        description="Rank opportunities using cross-agent executive scores",
        schedule_hour=6,
        schedule_minute=0,
        arq_jobs=("executive_ranking",),
    ),
    SchedulerJobDefinition(
        job_name="venture_report",
        display_name="Venture Report",
        description="Generate executive venture recommendation reports",
        schedule_hour=7,
        schedule_minute=0,
        arq_jobs=("venture_report",),
    ),
)

SCHEDULER_JOB_MAP: dict[str, SchedulerJobDefinition] = {
    job.job_name: job for job in DEFAULT_SCHEDULER_JOBS
}


def get_job_definition(job_name: str) -> SchedulerJobDefinition | None:
    return SCHEDULER_JOB_MAP.get(job_name)
