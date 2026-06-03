"""Go-to-market REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.agents.go_to_market.schemas import GoToMarketBatchResult, GoToMarketResult
from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import GTMPlanStatus
from app.schemas.filters import GTMPlanListFilter
from app.schemas.gtm_plan import GTMPlanDetail, GTMPlanRead
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/go-to-market", tags=["go-to-market"])


def _gtm_plan_filters(
    opportunity_id: Annotated[UUID | None, Query(description="Filter by opportunity ID")] = None,
    status_filter: Annotated[
        GTMPlanStatus | None,
        Query(alias="status", description="Filter by GTM plan status"),
    ] = None,
    is_current: Annotated[bool | None, Query(description="Filter by current plan flag")] = None,
    min_confidence_score: Annotated[
        int | None,
        Query(ge=0, le=100, description="Minimum GTM confidence score"),
    ] = None,
    max_estimated_cac_usd: Annotated[
        float | None,
        Query(ge=0, description="Maximum estimated CAC in USD"),
    ] = None,
    min_gtm_readiness_score: Annotated[
        int | None,
        Query(ge=0, le=100, description="Minimum GTM readiness score for ranking"),
    ] = None,
) -> GTMPlanListFilter:
    return GTMPlanListFilter(
        opportunity_id=opportunity_id,
        status=status_filter,
        is_current=is_current,
        min_confidence_score=min_confidence_score,
        max_estimated_cac_usd=max_estimated_cac_usd,
        min_gtm_readiness_score=min_gtm_readiness_score,
    )


@router.get(
    "",
    response_model=PaginatedResponse[GTMPlanRead],
    summary="List go-to-market plans",
)
async def list_gtm_plans(
    services: Services,
    pagination: Pagination,
    filters: Annotated[GTMPlanListFilter, Depends(_gtm_plan_filters)],
) -> PaginatedResponse[GTMPlanRead]:
    return await services.go_to_market.list_plans(filters, pagination)


@router.post(
    "/generate",
    response_model=GoToMarketBatchResult,
    status_code=status.HTTP_201_CREATED,
    summary="Batch generate go-to-market plans",
)
async def generate_gtm_plan_batch(
    services: Services,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    force: Annotated[bool, Query(description="Re-plan even if current exists")] = False,
) -> GoToMarketBatchResult:
    return await services.go_to_market.plan_pending(limit=limit, force=force)


@router.get(
    "/opportunities/{opportunity_id}/current",
    response_model=GTMPlanDetail,
    summary="Get current go-to-market plan",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Go-to-market plan not found"}},
)
async def get_current_gtm_plan(
    opportunity_id: UUID,
    services: Services,
) -> GTMPlanDetail:
    return await services.go_to_market.get_current_plan(opportunity_id)


@router.get(
    "/opportunities/{opportunity_id}/history",
    response_model=list[GTMPlanRead],
    summary="List go-to-market plan history",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def list_gtm_plan_history(
    opportunity_id: UUID,
    services: Services,
) -> list[GTMPlanRead]:
    return await services.go_to_market.list_history(opportunity_id)


@router.post(
    "/opportunities/{opportunity_id}/generate",
    response_model=GoToMarketResult,
    status_code=status.HTTP_201_CREATED,
    summary="Generate go-to-market plan for opportunity",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def generate_gtm_plan(
    opportunity_id: UUID,
    services: Services,
    force: Annotated[bool, Query(description="Re-plan even if current exists")] = False,
) -> GoToMarketResult:
    return await services.go_to_market.plan_opportunity(opportunity_id, force=force)


@router.get(
    "/{plan_id}",
    response_model=GTMPlanDetail,
    summary="Get go-to-market plan",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Go-to-market plan not found"}},
)
async def get_gtm_plan(
    plan_id: UUID,
    services: Services,
) -> GTMPlanDetail:
    return await services.go_to_market.get_plan(plan_id)
