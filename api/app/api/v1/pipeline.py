"""Pipeline orchestration REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import JobEnqueuerDep, Services
from app.api.pagination import Pagination
from app.schemas.pagination import PaginatedResponse
from app.schemas.pipeline import PipelineRunDetail, PipelineRunRead, PipelineRunRequest, PipelineRunResult
from app.workers.schemas import JobEnqueueResult

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post(
    "/run",
    responses={
        status.HTTP_201_CREATED: {"model": PipelineRunResult},
        status.HTTP_202_ACCEPTED: {"model": JobEnqueueResult},
    },
    summary="Run the full Venture Studio pipeline",
    description=(
        "Execute all pipeline stages sequentially. Set background=true to enqueue an ARQ worker job."
    ),
)
async def run_pipeline(
    services: Services,
    enqueuer: JobEnqueuerDep,
    response: Response,
    request: PipelineRunRequest | None = None,
    background: Annotated[
        bool,
        Query(description="When true, enqueue pipeline run on ARQ worker instead of blocking"),
    ] = False,
) -> PipelineRunResult | JobEnqueueResult:
    body = request or PipelineRunRequest()
    if background:
        response.status_code = status.HTTP_202_ACCEPTED
        return await enqueuer.enqueue_pipeline(
            trigger=body.trigger,
            options=body.options,
        )
    response.status_code = status.HTTP_201_CREATED
    return await services.pipeline.run_pipeline(
        trigger=body.trigger,
        options=body.options,
    )


@router.get(
    "/runs",
    response_model=PaginatedResponse[PipelineRunRead],
    summary="List pipeline runs",
)
async def list_pipeline_runs(
    services: Services,
    pagination: Pagination,
) -> PaginatedResponse[PipelineRunRead]:
    return await services.pipeline.list_runs(pagination)


@router.get(
    "/runs/{run_id}",
    response_model=PipelineRunDetail,
    summary="Get pipeline run detail",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Pipeline run not found"}},
)
async def get_pipeline_run(
    run_id: UUID,
    services: Services,
) -> PipelineRunDetail:
    return await services.pipeline.get_run(run_id)
