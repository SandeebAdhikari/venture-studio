"""Background job REST endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import JobEnqueuerDep
from app.db.enums import PipelineTrigger
from app.schemas.pagination import PaginatedResponse
from app.workers.jobs import STAGE_JOB_MAP
from app.workers.schemas import JobEnqueueResult, JobOptions, JobRecord, RunPipelineJobRequest, RunStageJobRequest

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "",
    response_model=PaginatedResponse[JobRecord],
    summary="List recent background jobs",
)
async def list_jobs(
    enqueuer: JobEnqueuerDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[JobRecord]:
    items = await enqueuer.list_recent_jobs(limit=limit)
    return PaginatedResponse[JobRecord](
        items=items,
        total=len(items),
        limit=limit,
        offset=0,
    )


@router.get(
    "/{job_id}",
    response_model=JobRecord,
    summary="Get background job status",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Job not found"}},
)
async def get_job(job_id: str, enqueuer: JobEnqueuerDep) -> JobRecord:
    record = await enqueuer.get_job(job_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{job_id}' not found")
    return record


@router.post(
    "/run-pipeline",
    response_model=JobEnqueueResult,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue full pipeline run",
)
async def enqueue_pipeline_job(
    enqueuer: JobEnqueuerDep,
    request: RunPipelineJobRequest | None = None,
) -> JobEnqueueResult:
    body = request or RunPipelineJobRequest()
    return await enqueuer.enqueue_pipeline(
        trigger=PipelineTrigger(body.trigger),
        options=body.options,
    )


@router.post(
    "/{job_name}",
    response_model=JobEnqueueResult,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue a pipeline stage job",
    responses={status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Unknown job name"}},
)
async def enqueue_stage_job(
    job_name: str,
    enqueuer: JobEnqueuerDep,
    request: RunStageJobRequest | None = None,
) -> JobEnqueueResult:
    if job_name not in STAGE_JOB_MAP:
        from app.exceptions import ValidationError

        raise ValidationError(
            f"Unknown job '{job_name}'. Valid stage jobs: {sorted(STAGE_JOB_MAP.keys())}"
        )
    body = request or RunStageJobRequest()
    return await enqueuer.enqueue_stage(job_name, options=body.options)
