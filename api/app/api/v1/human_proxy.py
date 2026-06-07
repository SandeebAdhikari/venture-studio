"""Human proxy REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.agents.human_proxy.schemas import HumanProxyBatchResult, HumanProxyReevalResult, HumanProxyResult
from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import FounderRecommendation, HumanProxyEvaluationStatus
from app.schemas.filters import HumanProxyEvaluationListFilter
from app.schemas.founder_profile import FounderProfileCreate, FounderProfileRead
from app.schemas.human_proxy_evaluation import HumanProxyEvaluationDetail, HumanProxyEvaluationRead
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/human-proxy", tags=["human-proxy"])


def _human_proxy_evaluation_filters(
    opportunity_id: Annotated[UUID | None, Query(description="Filter by opportunity ID")] = None,
    founder_profile_id: Annotated[
        UUID | None,
        Query(description="Filter by founder profile ID"),
    ] = None,
    status_filter: Annotated[
        HumanProxyEvaluationStatus | None,
        Query(alias="status", description="Filter by evaluation status"),
    ] = None,
    is_current: Annotated[
        bool | None, Query(description="Filter by current evaluation flag")
    ] = None,
    min_founder_fit_score: Annotated[
        int | None,
        Query(ge=0, le=100, description="Minimum founder fit score"),
    ] = None,
    min_feasibility_score: Annotated[
        int | None,
        Query(ge=0, le=100, description="Minimum feasibility score"),
    ] = None,
    recommendation: Annotated[
        FounderRecommendation | None,
        Query(description="Filter by recommendation"),
    ] = None,
    min_ranking_score: Annotated[
        int | None,
        Query(ge=0, le=100, description="Minimum ranking score"),
    ] = None,
) -> HumanProxyEvaluationListFilter:
    return HumanProxyEvaluationListFilter(
        opportunity_id=opportunity_id,
        founder_profile_id=founder_profile_id,
        status=status_filter,
        is_current=is_current,
        min_founder_fit_score=min_founder_fit_score,
        min_feasibility_score=min_feasibility_score,
        recommendation=recommendation,
        min_ranking_score=min_ranking_score,
    )


@router.get(
    "",
    response_model=PaginatedResponse[HumanProxyEvaluationRead],
    summary="List human proxy evaluations",
)
async def list_human_proxy_evaluations(
    services: Services,
    pagination: Pagination,
    filters: Annotated[HumanProxyEvaluationListFilter, Depends(_human_proxy_evaluation_filters)],
) -> PaginatedResponse[HumanProxyEvaluationRead]:
    return await services.human_proxy.list_evaluations(filters, pagination)


@router.post(
    "/generate",
    response_model=HumanProxyBatchResult,
    status_code=status.HTTP_201_CREATED,
    summary="Batch evaluate opportunities against a founder profile",
)
async def generate_human_proxy_evaluation_batch(
    services: Services,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    force: Annotated[bool, Query(description="Re-evaluate even if current exists")] = False,
    founder_profile_id: Annotated[
        UUID | None,
        Query(description="Founder profile to use; defaults to system profile"),
    ] = None,
) -> HumanProxyBatchResult:
    return await services.human_proxy.evaluate_pending(
        limit=limit,
        force=force,
        founder_profile_id=founder_profile_id,
    )


@router.post(
    "/reevaluate-current",
    response_model=HumanProxyReevalResult,
    status_code=status.HTTP_201_CREATED,
    summary="Re-evaluate current legacy human proxy evaluations with the modern pipeline",
)
async def reevaluate_current_human_proxy_evaluations(
    services: Services,
    founder_profile_id: Annotated[
        UUID | None,
        Query(description="Limit re-evaluation to one founder profile"),
    ] = None,
    legacy_only: Annotated[
        bool,
        Query(description="Only re-evaluate rows with scale_version=legacy"),
    ] = True,
    dry_run: Annotated[
        bool,
        Query(description="Identify targets without invoking the LLM"),
    ] = False,
) -> HumanProxyReevalResult:
    return await services.human_proxy.reevaluate_current(
        founder_profile_id=founder_profile_id,
        legacy_only=legacy_only,
        dry_run=dry_run,
    )


@router.get(
    "/founder-profiles",
    response_model=list[FounderProfileRead],
    summary="List active founder profiles",
)
async def list_founder_profiles(services: Services) -> list[FounderProfileRead]:
    return await services.human_proxy.list_profiles()


@router.post(
    "/founder-profiles",
    response_model=FounderProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a founder profile",
)
async def create_founder_profile(
    services: Services,
    data: FounderProfileCreate,
) -> FounderProfileRead:
    return await services.human_proxy.create_profile(data)


@router.get(
    "/founder-profiles/{profile_id}",
    response_model=FounderProfileRead,
    summary="Get founder profile",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Founder profile not found"}},
)
async def get_founder_profile(
    profile_id: UUID,
    services: Services,
) -> FounderProfileRead:
    return await services.human_proxy.get_profile(profile_id)


@router.get(
    "/opportunities/{opportunity_id}/current",
    response_model=HumanProxyEvaluationDetail,
    summary="Get current human proxy evaluation",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Human proxy evaluation not found"}},
)
async def get_current_human_proxy_evaluation(
    opportunity_id: UUID,
    services: Services,
    founder_profile_id: Annotated[
        UUID | None,
        Query(description="Founder profile to use; defaults to system profile"),
    ] = None,
) -> HumanProxyEvaluationDetail:
    return await services.human_proxy.get_current_evaluation(
        opportunity_id,
        founder_profile_id=founder_profile_id,
    )


@router.get(
    "/opportunities/{opportunity_id}/history",
    response_model=list[HumanProxyEvaluationRead],
    summary="List human proxy evaluation history",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def list_human_proxy_evaluation_history(
    opportunity_id: UUID,
    services: Services,
    founder_profile_id: Annotated[
        UUID | None,
        Query(description="Founder profile to use; defaults to system profile"),
    ] = None,
) -> list[HumanProxyEvaluationRead]:
    return await services.human_proxy.list_history(
        opportunity_id,
        founder_profile_id=founder_profile_id,
    )


@router.post(
    "/opportunities/{opportunity_id}/generate",
    response_model=HumanProxyResult,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate opportunity against a founder profile",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def generate_human_proxy_evaluation(
    opportunity_id: UUID,
    services: Services,
    force: Annotated[bool, Query(description="Re-evaluate even if current exists")] = False,
    founder_profile_id: Annotated[
        UUID | None,
        Query(description="Founder profile to use; defaults to system profile"),
    ] = None,
) -> HumanProxyResult:
    return await services.human_proxy.evaluate_opportunity(
        opportunity_id,
        founder_profile_id=founder_profile_id,
        force=force,
    )


@router.get(
    "/{evaluation_id}",
    response_model=HumanProxyEvaluationDetail,
    summary="Get human proxy evaluation",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Human proxy evaluation not found"}},
)
async def get_human_proxy_evaluation(
    evaluation_id: UUID,
    services: Services,
) -> HumanProxyEvaluationDetail:
    return await services.human_proxy.get_evaluation(evaluation_id)
