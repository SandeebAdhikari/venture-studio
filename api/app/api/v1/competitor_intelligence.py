"""Competitor intelligence REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.agents.competitor_intelligence.schemas import (
    CompetitorAnalysisBatchResult,
    CompetitorAnalysisResult,
)
from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import CompetitorAnalysisStatus
from app.schemas.competitor_analysis import CompetitorAnalysisDetail, CompetitorAnalysisRead
from app.schemas.filters import CompetitorAnalysisListFilter
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/competitor-intelligence", tags=["competitor-intelligence"])


def _competitor_analysis_filters(
    opportunity_id: Annotated[UUID | None, Query(description="Filter by opportunity ID")] = None,
    status_filter: Annotated[
        CompetitorAnalysisStatus | None,
        Query(alias="status", description="Filter by analysis status"),
    ] = None,
    is_current: Annotated[bool | None, Query(description="Filter by current analysis flag")] = None,
) -> CompetitorAnalysisListFilter:
    return CompetitorAnalysisListFilter(
        opportunity_id=opportunity_id,
        status=status_filter,
        is_current=is_current,
    )


@router.get(
    "",
    response_model=PaginatedResponse[CompetitorAnalysisRead],
    summary="List competitor analyses",
    description="Return stored competitor intelligence analyses.",
)
async def list_competitor_analyses(
    services: Services,
    pagination: Pagination,
    filters: Annotated[CompetitorAnalysisListFilter, Depends(_competitor_analysis_filters)],
) -> PaginatedResponse[CompetitorAnalysisRead]:
    return await services.competitor_intelligence.list_analyses(filters, pagination)


@router.post(
    "/generate",
    response_model=CompetitorAnalysisBatchResult,
    status_code=status.HTTP_201_CREATED,
    summary="Batch generate competitor intelligence",
    description="Analyze competitors for opportunities without a current analysis.",
)
async def generate_competitor_intelligence_batch(
    services: Services,
    limit: Annotated[int, Query(ge=1, le=100, description="Max opportunities to analyze")] = 20,
    force: Annotated[
        bool,
        Query(description="Re-analyze even if a current analysis exists"),
    ] = False,
) -> CompetitorAnalysisBatchResult:
    return await services.competitor_intelligence.analyze_pending(limit=limit, force=force)


@router.get(
    "/opportunities/{opportunity_id}/current",
    response_model=CompetitorAnalysisDetail,
    summary="Get current competitor analysis",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Competitor analysis not found"}},
)
async def get_current_competitor_analysis(
    opportunity_id: UUID,
    services: Services,
) -> CompetitorAnalysisDetail:
    return await services.competitor_intelligence.get_current_analysis(opportunity_id)


@router.get(
    "/opportunities/{opportunity_id}/history",
    response_model=list[CompetitorAnalysisRead],
    summary="List competitor analysis history",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def list_competitor_analysis_history(
    opportunity_id: UUID,
    services: Services,
) -> list[CompetitorAnalysisRead]:
    return await services.competitor_intelligence.list_history(opportunity_id)


@router.post(
    "/opportunities/{opportunity_id}/generate",
    response_model=CompetitorAnalysisResult,
    status_code=status.HTTP_201_CREATED,
    summary="Generate competitor intelligence for opportunity",
    description="Analyze competitors for a single opportunity.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def generate_competitor_intelligence(
    opportunity_id: UUID,
    services: Services,
    force: Annotated[
        bool,
        Query(description="Re-analyze even if a current analysis exists"),
    ] = False,
) -> CompetitorAnalysisResult:
    return await services.competitor_intelligence.analyze_opportunity(opportunity_id, force=force)


@router.get(
    "/{analysis_id}",
    response_model=CompetitorAnalysisDetail,
    summary="Get competitor analysis",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Competitor analysis not found"}},
)
async def get_competitor_analysis(
    analysis_id: UUID, services: Services
) -> CompetitorAnalysisDetail:
    return await services.competitor_intelligence.get_analysis(analysis_id)
