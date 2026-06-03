"""Executive ranking REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import Services
from app.api.pagination import Pagination
from app.ranking.schemas import ExecutiveRankingResult
from app.schemas.executive_ranking import ExecutiveRankingRunDetail, ExecutiveRankingRunRead
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/executive-ranking", tags=["executive-ranking"])


@router.post(
    "/generate",
    response_model=ExecutiveRankingResult,
    status_code=status.HTTP_201_CREATED,
    summary="Generate executive opportunity ranking",
    description="Rank all opportunities using outputs from prior agents and return the top opportunities.",
)
async def generate_executive_ranking(
    services: Services,
    top_n: Annotated[int, Query(ge=1, le=50, description="Number of top opportunities to highlight")] = 5,
    founder_profile_id: Annotated[
        UUID | None,
        Query(description="Founder profile for human proxy scores; defaults to system profile"),
    ] = None,
) -> ExecutiveRankingResult:
    return await services.executive_ranking.generate_ranking(
        top_n=top_n,
        founder_profile_id=founder_profile_id,
    )


@router.get(
    "/current",
    response_model=ExecutiveRankingRunDetail,
    summary="Get current executive ranking",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Executive ranking not found"}},
)
async def get_current_executive_ranking(services: Services) -> ExecutiveRankingRunDetail:
    return await services.executive_ranking.get_current_ranking()


@router.get(
    "/history",
    response_model=PaginatedResponse[ExecutiveRankingRunRead],
    summary="List executive ranking history",
)
async def list_executive_ranking_history(
    services: Services,
    pagination: Pagination,
) -> PaginatedResponse[ExecutiveRankingRunRead]:
    return await services.executive_ranking.list_history(pagination)


@router.get(
    "/{run_id}",
    response_model=ExecutiveRankingRunDetail,
    summary="Get executive ranking run",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Executive ranking run not found"}},
)
async def get_executive_ranking(
    run_id: UUID,
    services: Services,
) -> ExecutiveRankingRunDetail:
    return await services.executive_ranking.get_ranking(run_id)
