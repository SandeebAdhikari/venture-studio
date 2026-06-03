"""Growth strategy REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.agents.growth_strategy.schemas import GrowthStrategyBatchResult, GrowthStrategyResult
from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import GrowthEvaluationStatus
from app.schemas.filters import GrowthEvaluationListFilter
from app.schemas.growth_evaluation import GrowthEvaluationDetail, GrowthEvaluationRead
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/growth-strategy", tags=["growth-strategy"])


def _growth_evaluation_filters(
    opportunity_id: Annotated[UUID | None, Query(description="Filter by opportunity ID")] = None,
    status_filter: Annotated[
        GrowthEvaluationStatus | None,
        Query(alias="status", description="Filter by evaluation status"),
    ] = None,
    is_current: Annotated[
        bool | None, Query(description="Filter by current evaluation flag")
    ] = None,
    min_growth_score: Annotated[
        int | None,
        Query(ge=0, le=100, description="Minimum growth score"),
    ] = None,
    min_scalability_score: Annotated[
        int | None,
        Query(ge=0, le=100, description="Minimum scalability score"),
    ] = None,
    max_risk_score: Annotated[
        int | None,
        Query(ge=0, le=100, description="Maximum risk score"),
    ] = None,
    min_growth_readiness_score: Annotated[
        int | None,
        Query(ge=0, le=100, description="Minimum growth readiness score"),
    ] = None,
) -> GrowthEvaluationListFilter:
    return GrowthEvaluationListFilter(
        opportunity_id=opportunity_id,
        status=status_filter,
        is_current=is_current,
        min_growth_score=min_growth_score,
        min_scalability_score=min_scalability_score,
        max_risk_score=max_risk_score,
        min_growth_readiness_score=min_growth_readiness_score,
    )


@router.get(
    "",
    response_model=PaginatedResponse[GrowthEvaluationRead],
    summary="List growth evaluations",
)
async def list_growth_evaluations(
    services: Services,
    pagination: Pagination,
    filters: Annotated[GrowthEvaluationListFilter, Depends(_growth_evaluation_filters)],
) -> PaginatedResponse[GrowthEvaluationRead]:
    return await services.growth_strategy.list_evaluations(filters, pagination)


@router.post(
    "/generate",
    response_model=GrowthStrategyBatchResult,
    status_code=status.HTTP_201_CREATED,
    summary="Batch generate growth evaluations",
)
async def generate_growth_evaluation_batch(
    services: Services,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    force: Annotated[bool, Query(description="Re-evaluate even if current exists")] = False,
) -> GrowthStrategyBatchResult:
    return await services.growth_strategy.evaluate_pending(limit=limit, force=force)


@router.get(
    "/opportunities/{opportunity_id}/current",
    response_model=GrowthEvaluationDetail,
    summary="Get current growth evaluation",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Growth evaluation not found"}},
)
async def get_current_growth_evaluation(
    opportunity_id: UUID,
    services: Services,
) -> GrowthEvaluationDetail:
    return await services.growth_strategy.get_current_evaluation(opportunity_id)


@router.get(
    "/opportunities/{opportunity_id}/history",
    response_model=list[GrowthEvaluationRead],
    summary="List growth evaluation history",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def list_growth_evaluation_history(
    opportunity_id: UUID,
    services: Services,
) -> list[GrowthEvaluationRead]:
    return await services.growth_strategy.list_history(opportunity_id)


@router.post(
    "/opportunities/{opportunity_id}/generate",
    response_model=GrowthStrategyResult,
    status_code=status.HTTP_201_CREATED,
    summary="Generate growth evaluation for opportunity",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def generate_growth_evaluation(
    opportunity_id: UUID,
    services: Services,
    force: Annotated[bool, Query(description="Re-evaluate even if current exists")] = False,
) -> GrowthStrategyResult:
    return await services.growth_strategy.evaluate_opportunity(opportunity_id, force=force)


@router.get(
    "/{evaluation_id}",
    response_model=GrowthEvaluationDetail,
    summary="Get growth evaluation",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Growth evaluation not found"}},
)
async def get_growth_evaluation(
    evaluation_id: UUID,
    services: Services,
) -> GrowthEvaluationDetail:
    return await services.growth_strategy.get_evaluation(evaluation_id)
