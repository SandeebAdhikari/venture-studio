"""Founder approval workflow REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import ApprovalStatus, ApprovalSubjectType
from app.schemas.approval import (
    ApprovalActionRequest,
    ApprovalActionResult,
    ApprovalListFilter,
    ApprovalRequestRead,
)
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _approval_filters(
    status: Annotated[ApprovalStatus | None, Query()] = None,
    subject_type: Annotated[ApprovalSubjectType | None, Query()] = None,
) -> ApprovalListFilter:
    return ApprovalListFilter(status=status, subject_type=subject_type)


@router.get(
    "",
    response_model=PaginatedResponse[ApprovalRequestRead],
    summary="List founder approval requests",
)
async def list_approvals(
    services: Services,
    pagination: Pagination,
    filters: ApprovalListFilter = Depends(_approval_filters),
) -> PaginatedResponse[ApprovalRequestRead]:
    return await services.approval.list_approvals(filters, pagination)


@router.post(
    "/{approval_id}/approve",
    response_model=ApprovalActionResult,
    summary="Approve a ranking or venture report",
)
async def approve_request(
    approval_id: UUID,
    services: Services,
    data: ApprovalActionRequest | None = None,
) -> ApprovalActionResult:
    return await services.approval.approve(approval_id, data or ApprovalActionRequest())


@router.post(
    "/{approval_id}/reject",
    response_model=ApprovalActionResult,
    summary="Reject a ranking or venture report",
)
async def reject_request(
    approval_id: UUID,
    services: Services,
    data: ApprovalActionRequest | None = None,
) -> ApprovalActionResult:
    return await services.approval.reject(approval_id, data or ApprovalActionRequest())


@router.post(
    "/{approval_id}/research",
    response_model=ApprovalActionResult,
    summary="Request additional research before approval",
    responses={status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Comment required"}},
)
async def request_more_research(
    approval_id: UUID,
    services: Services,
    data: ApprovalActionRequest,
) -> ApprovalActionResult:
    return await services.approval.request_research(approval_id, data)
