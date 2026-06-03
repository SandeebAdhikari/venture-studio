"""Revenue validation REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.agents.revenue_validation.schemas import RevenueValidationBatchResult, RevenueValidationResult
from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import RevenueValidationStatus
from app.schemas.filters import RevenueValidationListFilter
from app.schemas.pagination import PaginatedResponse
from app.schemas.revenue_validation import RevenueValidationDetail, RevenueValidationRead

router = APIRouter(prefix="/revenue-validation", tags=["revenue-validation"])


def _revenue_validation_filters(
    opportunity_id: Annotated[UUID | None, Query(description="Filter by opportunity ID")] = None,
    status_filter: Annotated[
        RevenueValidationStatus | None,
        Query(alias="status", description="Filter by validation status"),
    ] = None,
    is_current: Annotated[bool | None, Query(description="Filter by current validation flag")] = None,
    min_willingness_to_pay: Annotated[
        int | None,
        Query(ge=0, le=100, description="Minimum willingness-to-pay score"),
    ] = None,
) -> RevenueValidationListFilter:
    return RevenueValidationListFilter(
        opportunity_id=opportunity_id,
        status=status_filter,
        is_current=is_current,
        min_willingness_to_pay=min_willingness_to_pay,
    )


@router.get(
    "",
    response_model=PaginatedResponse[RevenueValidationRead],
    summary="List revenue validations",
)
async def list_revenue_validations(
    services: Services,
    pagination: Pagination,
    filters: Annotated[RevenueValidationListFilter, Depends(_revenue_validation_filters)],
) -> PaginatedResponse[RevenueValidationRead]:
    return await services.revenue_validation.list_validations(filters, pagination)


@router.post(
    "/generate",
    response_model=RevenueValidationBatchResult,
    status_code=status.HTTP_201_CREATED,
    summary="Batch generate revenue validation",
)
async def generate_revenue_validation_batch(
    services: Services,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    force: Annotated[bool, Query(description="Re-validate even if current exists")] = False,
) -> RevenueValidationBatchResult:
    return await services.revenue_validation.validate_pending(limit=limit, force=force)


@router.get(
    "/opportunities/{opportunity_id}/current",
    response_model=RevenueValidationDetail,
    summary="Get current revenue validation",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Revenue validation not found"}},
)
async def get_current_revenue_validation(
    opportunity_id: UUID,
    services: Services,
) -> RevenueValidationDetail:
    return await services.revenue_validation.get_current_validation(opportunity_id)


@router.get(
    "/opportunities/{opportunity_id}/history",
    response_model=list[RevenueValidationRead],
    summary="List revenue validation history",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def list_revenue_validation_history(
    opportunity_id: UUID,
    services: Services,
) -> list[RevenueValidationRead]:
    return await services.revenue_validation.list_history(opportunity_id)


@router.post(
    "/opportunities/{opportunity_id}/generate",
    response_model=RevenueValidationResult,
    status_code=status.HTTP_201_CREATED,
    summary="Generate revenue validation for opportunity",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def generate_revenue_validation(
    opportunity_id: UUID,
    services: Services,
    force: Annotated[bool, Query(description="Re-validate even if current exists")] = False,
) -> RevenueValidationResult:
    return await services.revenue_validation.validate_opportunity(opportunity_id, force=force)


@router.get(
    "/{validation_id}",
    response_model=RevenueValidationDetail,
    summary="Get revenue validation",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Revenue validation not found"}},
)
async def get_revenue_validation(
    validation_id: UUID,
    services: Services,
) -> RevenueValidationDetail:
    return await services.revenue_validation.get_validation(validation_id)
