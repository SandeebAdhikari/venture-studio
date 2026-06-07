"""Venture report regeneration REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import Services
from app.reports.venture.schemas import VentureReportRegenResult

router = APIRouter(prefix="/venture-reports", tags=["venture-reports"])


@router.post(
    "/regenerate-current",
    response_model=VentureReportRegenResult,
    status_code=status.HTTP_201_CREATED,
    summary="Regenerate venture report from current ranking and human proxy evaluations",
    description=(
        "Create a new venture recommendation report pinned to the current executive "
        "ranking run and current agent outputs. Prior reports are preserved."
    ),
)
async def regenerate_current_venture_reports(
    services: Services,
    top_n: Annotated[
        int, Query(ge=1, le=50, description="Number of top opportunities to include")
    ] = 5,
    founder_profile_id: Annotated[
        UUID | None,
        Query(description="Founder profile for human proxy sections"),
    ] = None,
    dry_run: Annotated[
        bool,
        Query(description="Preview regeneration without creating a new report"),
    ] = False,
    publish: Annotated[
        bool,
        Query(description="Publish report immediately when not in dry-run mode"),
    ] = True,
) -> VentureReportRegenResult:
    return await services.venture_reports.regenerate_current_reports(
        top_n=top_n,
        founder_profile_id=founder_profile_id,
        dry_run=dry_run,
        publish=publish,
    )
