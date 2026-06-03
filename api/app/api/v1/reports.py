"""Report REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import ReportStatus, ReportType
from app.reports.executive.schemas import ExecutiveReportResult, ReportMarkdownRead
from app.schemas.filters import ReportListFilter
from app.schemas.pagination import PaginatedResponse
from app.schemas.report import ReportCreate, ReportRead, ReportUpdate

router = APIRouter(prefix="/reports", tags=["reports"])


def _report_filters(
    opportunity_id: Annotated[UUID | None, Query(description="Filter by opportunity ID")] = None,
    report_type: Annotated[ReportType | None, Query(description="Filter by report type")] = None,
    status_filter: Annotated[
        ReportStatus | None,
        Query(alias="status", description="Filter by report status"),
    ] = None,
) -> ReportListFilter:
    return ReportListFilter(
        opportunity_id=opportunity_id,
        report_type=report_type,
        status=status_filter,
    )


@router.get(
    "",
    response_model=PaginatedResponse[ReportRead],
    summary="List reports",
    description="Return generated reports and digests.",
)
async def list_reports(
    services: Services,
    pagination: Pagination,
    filters: Annotated[ReportListFilter, Depends(_report_filters)],
) -> PaginatedResponse[ReportRead]:
    return await services.reports.list_reports(filters, pagination)


@router.get(
    "/{report_id}",
    response_model=ReportRead,
    summary="Get report",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Report not found"}},
)
async def get_report(report_id: UUID, services: Services) -> ReportRead:
    return await services.reports.get_report(report_id)


@router.post(
    "",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create report",
    responses={status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"}},
)
async def create_report(data: ReportCreate, services: Services) -> ReportRead:
    return await services.reports.create_report(data)


@router.patch(
    "/{report_id}",
    response_model=ReportRead,
    summary="Update report",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Report not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"},
    },
)
async def update_report(report_id: UUID, data: ReportUpdate, services: Services) -> ReportRead:
    return await services.reports.update_report(report_id, data)


@router.post(
    "/{report_id}/publish",
    response_model=ReportRead,
    summary="Publish report",
    description="Mark a report as published.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Report not found"}},
)
async def publish_report(report_id: UUID, services: Services) -> ReportRead:
    return await services.reports.publish_report(report_id)


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete report",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Report not found"}},
)
async def delete_report(report_id: UUID, services: Services) -> None:
    await services.reports.delete_report(report_id)


@router.post(
    "/top-opportunities/generate",
    response_model=ExecutiveReportResult,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Top Opportunities report",
    description="Build a markdown executive report from top-scored opportunities and store it.",
)
async def generate_top_opportunities_report(
    services: Services,
    limit: Annotated[int, Query(ge=1, le=50, description="Max opportunities to include")] = 10,
    publish: Annotated[bool, Query(description="Publish report immediately")] = True,
) -> ExecutiveReportResult:
    return await services.executive_reports.generate_top_opportunities_report(
        limit=limit,
        publish=publish,
    )


@router.get(
    "/{report_id}/markdown",
    response_model=ReportMarkdownRead,
    summary="Get report markdown",
    description="Retrieve the markdown body of a stored report.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Report not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Report has no markdown content"},
    },
)
async def get_report_markdown(report_id: UUID, services: Services) -> ReportMarkdownRead:
    return await services.executive_reports.get_report_markdown(report_id)
