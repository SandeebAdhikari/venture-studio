"""Dashboard REST endpoints for Next.js consumption."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import JobEnqueuerDep, ObservabilityMetrics, Services
from app.api.pagination import Pagination
from app.schemas.dashboard import (
    DashboardJobSummary,
    DashboardOpportunitiesResponse,
    DashboardPipelineResponse,
    DashboardReportsResponse,
    DashboardSchedulerSummary,
    DashboardSummaryResponse,
)
from app.schemas.observability import DashboardObservabilityMetricsResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Dashboard overview snapshot",
    description=(
        "Aggregated pipeline, ingestion, opportunity, ranking, report, "
        "and background job metrics."
    ),
)
async def get_dashboard_summary(
    services: Services,
    enqueuer: JobEnqueuerDep,
) -> DashboardSummaryResponse:
    recent_jobs = await enqueuer.list_recent_jobs(limit=5)
    scheduler_jobs = await services.scheduler.list_jobs()
    return await services.dashboard.get_summary(
        recent_jobs=[
            DashboardJobSummary(
                job_id=job.job_id,
                job_name=job.job_name,
                status=job.status.value,
                finished_at=job.finished_at,
            )
            for job in recent_jobs
        ],
        scheduler_jobs=[
            DashboardSchedulerSummary(
                job_name=job.job_name,
                enabled=job.enabled,
                schedule_cron=job.schedule_cron,
                last_run_status=job.last_run.status.value if job.last_run else None,
                failure_count=job.failure_count,
            )
            for job in scheduler_jobs
        ],
    )


@router.get(
    "/metrics",
    response_model=DashboardObservabilityMetricsResponse,
    summary="Observability metrics snapshot",
    description=(
        "Pipeline, worker, scheduler, LLM, and approval metrics for dashboard monitoring."
    ),
)
async def get_dashboard_observability_metrics(
    observability: ObservabilityMetrics,
) -> DashboardObservabilityMetricsResponse:
    return await observability.get_dashboard_metrics()


@router.get(
    "/opportunities",
    response_model=DashboardOpportunitiesResponse,
    summary="Top opportunities and executive rankings",
)
async def get_dashboard_opportunities(
    services: Services,
    top_n: Annotated[int | None, Query(ge=1, le=50)] = None,
) -> DashboardOpportunitiesResponse:
    return await services.dashboard.get_opportunities(top_n=top_n)


@router.get(
    "/pipeline",
    response_model=DashboardPipelineResponse,
    summary="Pipeline runs and stage execution metrics",
)
async def get_dashboard_pipeline(
    services: Services,
    pagination: Pagination,
    include_stages: Annotated[bool, Query()] = True,
) -> DashboardPipelineResponse:
    return await services.dashboard.get_pipeline(
        limit=pagination.limit,
        offset=pagination.offset,
        include_stages=include_stages,
    )


@router.get(
    "/reports",
    response_model=DashboardReportsResponse,
    summary="Venture and executive reports for dashboard cards",
)
async def get_dashboard_reports(
    services: Services,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> DashboardReportsResponse:
    return await services.dashboard.get_reports(limit=limit)
