"""Opportunity REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import ReviewStatus
from app.schemas.filters import OpportunityListFilter
from app.schemas.opportunity import (
    OpportunityCreate,
    OpportunityDetail,
    OpportunityRead,
    OpportunityUpdate,
)
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


class LinkComplaintsRequest(BaseModel):
    complaint_ids: list[UUID]


class OpportunityReviewRequest(BaseModel):
    review_status: ReviewStatus
    review_notes: str | None = None


def _opportunity_filters(
    review_status: Annotated[
        ReviewStatus | None,
        Query(description="Filter by review status"),
    ] = None,
    min_confidence: Annotated[
        float | None,
        Query(ge=0.0, le=1.0, description="Minimum confidence score"),
    ] = None,
) -> OpportunityListFilter:
    return OpportunityListFilter(
        review_status=review_status,
        min_confidence=min_confidence,
    )


@router.get(
    "",
    response_model=PaginatedResponse[OpportunityRead],
    summary="List opportunities",
    description="Return synthesized business opportunities for founder review.",
)
async def list_opportunities(
    services: Services,
    pagination: Pagination,
    filters: Annotated[OpportunityListFilter, Depends(_opportunity_filters)],
) -> PaginatedResponse[OpportunityRead]:
    return await services.opportunities.list_opportunities(filters, pagination)


@router.get(
    "/{opportunity_id}",
    response_model=OpportunityDetail,
    summary="Get opportunity",
    description="Return an opportunity with linked evidence complaint IDs.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def get_opportunity(opportunity_id: UUID, services: Services) -> OpportunityDetail:
    return await services.opportunities.get_opportunity(opportunity_id)


@router.post(
    "",
    response_model=OpportunityDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create opportunity",
    responses={status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"}},
)
async def create_opportunity(data: OpportunityCreate, services: Services) -> OpportunityDetail:
    return await services.opportunities.create_opportunity(data)


@router.patch(
    "/{opportunity_id}",
    response_model=OpportunityRead,
    summary="Update opportunity",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def update_opportunity(
    opportunity_id: UUID,
    data: OpportunityUpdate,
    services: Services,
) -> OpportunityRead:
    return await services.opportunities.update_opportunity(opportunity_id, data)


@router.post(
    "/{opportunity_id}/review",
    response_model=OpportunityRead,
    summary="Review opportunity",
    description="Set review status and optional founder notes.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def review_opportunity(
    opportunity_id: UUID,
    data: OpportunityReviewRequest,
    services: Services,
) -> OpportunityRead:
    return await services.opportunities.set_review_status(
        opportunity_id,
        data.review_status,
        review_notes=data.review_notes,
    )


@router.post(
    "/{opportunity_id}/complaints",
    response_model=OpportunityDetail,
    summary="Link complaint evidence",
    description="Replace linked evidence complaints for an opportunity.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"},
    },
)
async def link_opportunity_complaints(
    opportunity_id: UUID,
    data: LinkComplaintsRequest,
    services: Services,
) -> OpportunityDetail:
    return await services.opportunities.link_complaints(opportunity_id, data.complaint_ids)
