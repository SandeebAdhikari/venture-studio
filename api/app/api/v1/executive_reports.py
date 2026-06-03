"""Executive venture recommendation report REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status
from fastapi.responses import Response

from app.api.deps import Services
from app.reports.venture.schemas import VentureReportMarkdownRead, VentureReportResult
from app.schemas.report import ReportRead

router = APIRouter(prefix="/executive-reports", tags=["executive-reports"])


@router.post(
    "/generate",
    response_model=VentureReportResult,
    status_code=status.HTTP_201_CREATED,
    summary="Generate venture recommendation report",
    description=(
        "Build a complete founder-readable report for the top ranked opportunities, "
        "including market, competitor, customer, revenue, product, GTM, growth, and fit analysis."
    ),
)
async def generate_venture_report(
    services: Services,
    top_n: Annotated[int, Query(ge=1, le=50, description="Number of top opportunities")] = 5,
    founder_profile_id: Annotated[
        UUID | None,
        Query(description="Founder profile for human proxy sections"),
    ] = None,
    ranking_run_id: Annotated[
        UUID | None,
        Query(description="Specific executive ranking run to use"),
    ] = None,
    generate_ranking_if_missing: Annotated[
        bool,
        Query(description="Generate executive ranking when none exists"),
    ] = True,
    publish: Annotated[bool, Query(description="Publish report immediately")] = True,
) -> VentureReportResult:
    return await services.venture_reports.generate_venture_report(
        top_n=top_n,
        founder_profile_id=founder_profile_id,
        ranking_run_id=ranking_run_id,
        generate_ranking_if_missing=generate_ranking_if_missing,
        publish=publish,
    )


@router.get(
    "/latest",
    response_model=ReportRead,
    summary="Get latest venture recommendation report",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Report not found"}},
)
async def get_latest_venture_report(services: Services) -> ReportRead:
    return await services.venture_reports.get_latest_report()


@router.get(
    "/{report_id}",
    response_model=ReportRead,
    summary="Get venture recommendation report",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Report not found"}},
)
async def get_venture_report(report_id: UUID, services: Services) -> ReportRead:
    return await services.venture_reports.get_report(report_id)


@router.get(
    "/{report_id}/markdown",
    response_model=VentureReportMarkdownRead,
    summary="Get venture report markdown",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Report not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Report has no markdown content"},
    },
)
async def get_venture_report_markdown(
    report_id: UUID,
    services: Services,
) -> VentureReportMarkdownRead:
    return await services.venture_reports.get_report_markdown(report_id)


@router.get(
    "/{report_id}/download",
    summary="Download venture report as markdown file",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Report not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Report has no markdown content"},
    },
)
async def download_venture_report(
    report_id: UUID,
    services: Services,
) -> Response:
    filename, markdown = await services.venture_reports.get_download_filename(report_id)
    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
