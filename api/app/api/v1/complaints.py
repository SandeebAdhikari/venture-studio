"""Complaint REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Services
from app.api.pagination import Pagination
from app.schemas.complaint import ComplaintCreate, ComplaintDetail, ComplaintRead, ComplaintUpdate
from app.schemas.filters import ComplaintListFilter
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/complaints", tags=["complaints"])


def _complaint_filters(
    category_id: Annotated[UUID | None, Query(description="Filter by category ID")] = None,
    domain_id: Annotated[UUID | None, Query(description="Filter by domain ID")] = None,
    persona_id: Annotated[UUID | None, Query(description="Filter by persona ID")] = None,
    min_severity: Annotated[int | None, Query(ge=1, le=5, description="Minimum severity")] = None,
    signal_id: Annotated[UUID | None, Query(description="Filter by source signal ID")] = None,
) -> ComplaintListFilter:
    return ComplaintListFilter(
        category_id=category_id,
        domain_id=domain_id,
        persona_id=persona_id,
        min_severity=min_severity,
        signal_id=signal_id,
    )


@router.get(
    "",
    response_model=PaginatedResponse[ComplaintRead],
    summary="List complaints",
    description="Return structured complaints extracted from ingested signals.",
)
async def list_complaints(
    services: Services,
    pagination: Pagination,
    filters: Annotated[ComplaintListFilter, Depends(_complaint_filters)],
) -> PaginatedResponse[ComplaintRead]:
    return await services.complaints.list_complaints(filters, pagination)


@router.get(
    "/{complaint_id}",
    response_model=ComplaintDetail,
    summary="Get complaint",
    description="Return a complaint with related category, domain, and persona details.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Complaint not found"}},
)
async def get_complaint(complaint_id: UUID, services: Services) -> ComplaintDetail:
    return await services.complaints.get_complaint(complaint_id)


@router.post(
    "",
    response_model=ComplaintRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create complaint",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Related entity not found"},
        status.HTTP_409_CONFLICT: {"description": "Complaint already exists for signal"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"},
    },
)
async def create_complaint(data: ComplaintCreate, services: Services) -> ComplaintRead:
    return await services.complaints.create_complaint(data)


@router.patch(
    "/{complaint_id}",
    response_model=ComplaintRead,
    summary="Update complaint",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Complaint not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"},
    },
)
async def update_complaint(
    complaint_id: UUID,
    data: ComplaintUpdate,
    services: Services,
) -> ComplaintRead:
    return await services.complaints.update_complaint(complaint_id, data)


@router.delete(
    "/{complaint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete complaint",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Complaint not found"}},
)
async def delete_complaint(complaint_id: UUID, services: Services) -> None:
    await services.complaints.delete_complaint(complaint_id)
