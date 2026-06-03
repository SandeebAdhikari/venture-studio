"""Product strategy REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.agents.product_strategy.schemas import ProductStrategyBatchResult, ProductStrategyResult
from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import ProductStrategyStatus
from app.schemas.filters import ProductStrategyListFilter
from app.schemas.pagination import PaginatedResponse
from app.schemas.product_strategy import ProductStrategyDetail, ProductStrategyRead

router = APIRouter(prefix="/product-strategy", tags=["product-strategy"])


def _product_strategy_filters(
    opportunity_id: Annotated[UUID | None, Query(description="Filter by opportunity ID")] = None,
    status_filter: Annotated[
        ProductStrategyStatus | None,
        Query(alias="status", description="Filter by strategy status"),
    ] = None,
    is_current: Annotated[bool | None, Query(description="Filter by current strategy flag")] = None,
    min_total_weeks: Annotated[
        int | None,
        Query(ge=1, description="Minimum estimated total weeks"),
    ] = None,
) -> ProductStrategyListFilter:
    return ProductStrategyListFilter(
        opportunity_id=opportunity_id,
        status=status_filter,
        is_current=is_current,
        min_total_weeks=min_total_weeks,
    )


@router.get(
    "",
    response_model=PaginatedResponse[ProductStrategyRead],
    summary="List product strategies",
)
async def list_product_strategies(
    services: Services,
    pagination: Pagination,
    filters: Annotated[ProductStrategyListFilter, Depends(_product_strategy_filters)],
) -> PaginatedResponse[ProductStrategyRead]:
    return await services.product_strategy.list_strategies(filters, pagination)


@router.post(
    "/generate",
    response_model=ProductStrategyBatchResult,
    status_code=status.HTTP_201_CREATED,
    summary="Batch generate product strategies",
)
async def generate_product_strategy_batch(
    services: Services,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    force: Annotated[bool, Query(description="Re-plan even if current exists")] = False,
) -> ProductStrategyBatchResult:
    return await services.product_strategy.plan_pending(limit=limit, force=force)


@router.get(
    "/opportunities/{opportunity_id}/current",
    response_model=ProductStrategyDetail,
    summary="Get current product strategy",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Product strategy not found"}},
)
async def get_current_product_strategy(
    opportunity_id: UUID,
    services: Services,
) -> ProductStrategyDetail:
    return await services.product_strategy.get_current_strategy(opportunity_id)


@router.get(
    "/opportunities/{opportunity_id}/history",
    response_model=list[ProductStrategyRead],
    summary="List product strategy history",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def list_product_strategy_history(
    opportunity_id: UUID,
    services: Services,
) -> list[ProductStrategyRead]:
    return await services.product_strategy.list_history(opportunity_id)


@router.post(
    "/opportunities/{opportunity_id}/generate",
    response_model=ProductStrategyResult,
    status_code=status.HTTP_201_CREATED,
    summary="Generate product strategy for opportunity",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def generate_product_strategy(
    opportunity_id: UUID,
    services: Services,
    force: Annotated[bool, Query(description="Re-plan even if current exists")] = False,
) -> ProductStrategyResult:
    return await services.product_strategy.plan_opportunity(opportunity_id, force=force)


@router.get(
    "/{strategy_id}",
    response_model=ProductStrategyDetail,
    summary="Get product strategy",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Product strategy not found"}},
)
async def get_product_strategy(
    strategy_id: UUID,
    services: Services,
) -> ProductStrategyDetail:
    return await services.product_strategy.get_strategy(strategy_id)
