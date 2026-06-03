"""Market research REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.agents.market_research.schemas import MarketResearchBatchResult, MarketResearchResult
from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import MarketResearchStatus
from app.schemas.filters import MarketBriefListFilter
from app.schemas.market_brief import MarketBriefRead
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/market-research", tags=["market-research"])


def _market_brief_filters(
    opportunity_id: Annotated[UUID | None, Query(description="Filter by opportunity ID")] = None,
    status_filter: Annotated[
        MarketResearchStatus | None,
        Query(alias="status", description="Filter by research status"),
    ] = None,
    is_current: Annotated[bool | None, Query(description="Filter by current brief flag")] = None,
) -> MarketBriefListFilter:
    return MarketBriefListFilter(
        opportunity_id=opportunity_id,
        status=status_filter,
        is_current=is_current,
    )


@router.get(
    "",
    response_model=PaginatedResponse[MarketBriefRead],
    summary="List market briefs",
    description="Return stored market intelligence briefs.",
)
async def list_market_briefs(
    services: Services,
    pagination: Pagination,
    filters: Annotated[MarketBriefListFilter, Depends(_market_brief_filters)],
) -> PaginatedResponse[MarketBriefRead]:
    return await services.market_research.list_briefs(filters, pagination)


@router.post(
    "/generate",
    response_model=MarketResearchBatchResult,
    status_code=status.HTTP_201_CREATED,
    summary="Batch generate market research",
    description="Research market intelligence for opportunities without a current brief.",
)
async def generate_market_research_batch(
    services: Services,
    limit: Annotated[int, Query(ge=1, le=100, description="Max opportunities to research")] = 20,
    force: Annotated[
        bool,
        Query(description="Re-research even if a current brief exists"),
    ] = False,
) -> MarketResearchBatchResult:
    return await services.market_research.research_pending(limit=limit, force=force)


@router.get(
    "/opportunities/{opportunity_id}/current",
    response_model=MarketBriefRead,
    summary="Get current market brief",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Market brief not found"}},
)
async def get_current_market_brief(
    opportunity_id: UUID,
    services: Services,
) -> MarketBriefRead:
    return await services.market_research.get_current_brief(opportunity_id)


@router.get(
    "/opportunities/{opportunity_id}/history",
    response_model=list[MarketBriefRead],
    summary="List market brief history",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def list_market_brief_history(
    opportunity_id: UUID,
    services: Services,
) -> list[MarketBriefRead]:
    return await services.market_research.list_history(opportunity_id)


@router.post(
    "/opportunities/{opportunity_id}/generate",
    response_model=MarketResearchResult,
    status_code=status.HTTP_201_CREATED,
    summary="Generate market research for opportunity",
    description="Research market intelligence for a single opportunity.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def generate_market_research(
    opportunity_id: UUID,
    services: Services,
    force: Annotated[
        bool,
        Query(description="Re-research even if a current brief exists"),
    ] = False,
) -> MarketResearchResult:
    return await services.market_research.research_opportunity(opportunity_id, force=force)


@router.get(
    "/{brief_id}",
    response_model=MarketBriefRead,
    summary="Get market brief",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Market brief not found"}},
)
async def get_market_brief(brief_id: UUID, services: Services) -> MarketBriefRead:
    return await services.market_research.get_brief(brief_id)
