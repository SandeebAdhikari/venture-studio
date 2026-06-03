"""Scheduler REST endpoints."""

from fastapi import APIRouter, status

from app.api.deps import JobEnqueuerDep, Services
from app.schemas.scheduler import SchedulerJobRead, SchedulerJobUpdate, SchedulerRunResult

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get(
    "/jobs",
    response_model=list[SchedulerJobRead],
    summary="List scheduled Venture Studio jobs",
    description=(
        "Returns configured cron jobs with schedule, enabled state, "
        "last run, and failure counts."
    ),
)
async def list_scheduler_jobs(services: Services) -> list[SchedulerJobRead]:
    return await services.scheduler.list_jobs()


@router.patch(
    "/jobs/{job_name}",
    response_model=SchedulerJobRead,
    summary="Enable or disable a scheduled job",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Scheduler job not found"}},
)
async def update_scheduler_job(
    job_name: str,
    data: SchedulerJobUpdate,
    services: Services,
) -> SchedulerJobRead:
    return await services.scheduler.update_job(job_name, data)


@router.post(
    "/run/{job_name}",
    response_model=SchedulerRunResult,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Manually trigger a scheduled job",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Scheduler job not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Job disabled or unknown"},
    },
)
async def run_scheduler_job(
    job_name: str,
    services: Services,
    enqueuer: JobEnqueuerDep,
) -> SchedulerRunResult:
    return await services.scheduler.trigger_job(job_name, enqueuer)
