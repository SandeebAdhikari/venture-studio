"""Pipeline orchestration REST endpoints."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import Services
from app.api.pagination import Pagination
from app.schemas.pagination import PaginatedResponse
from app.schemas.pipeline import PipelineRunDetail, PipelineRunRead, PipelineRunRequest, PipelineRunResult

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post(
    "/run",
    response_model=PipelineRunResult,
    status_code=status.HTTP_201_CREATED,
    summary="Run the full Venture Studio pipeline",
    description=(
        "Execute all pipeline stages sequentially: collect, classify, generate, score, "
        "eight analysis agents, executive ranking, and venture report."
    ),
)
async def run_pipeline(
    services: Services,
    request: PipelineRunRequest | None = None,
) -> PipelineRunResult:
    body = request or PipelineRunRequest()
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
