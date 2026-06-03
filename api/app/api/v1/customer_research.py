"""Customer research REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.agents.customer_research.schemas import CustomerResearchBatchResult, CustomerResearchResult
from app.api.deps import Services
from app.api.pagination import Pagination
from app.db.enums import CustomerResearchStatus
from app.schemas.customer_research import CustomerResearchDetail, CustomerResearchRead
from app.schemas.filters import CustomerResearchListFilter
from app.schemas.pagination import PaginatedResponse

router = APIRouter(prefix="/customer-research", tags=["customer-research"])


def _customer_research_filters(
    opportunity_id: Annotated[UUID | None, Query(description="Filter by opportunity ID")] = None,
    status_filter: Annotated[
        CustomerResearchStatus | None,
        Query(alias="status", description="Filter by research status"),
    ] = None,
    is_current: Annotated[bool | None, Query(description="Filter by current research flag")] = None,
    min_pain_score: Annotated[
        int | None,
        Query(ge=0, le=100, description="Minimum pain score"),
    ] = None,
    cares_verdict: Annotated[
        str | None,
        Query(description="Filter by cares verdict: yes, partial, no"),
    ] = None,
) -> CustomerResearchListFilter:
    return CustomerResearchListFilter(
        opportunity_id=opportunity_id,
        status=status_filter,
        is_current=is_current,
        min_pain_score=min_pain_score,
        cares_verdict=cares_verdict,
    )


@router.get(
    "",
    response_model=PaginatedResponse[CustomerResearchRead],
    summary="List customer research runs",
)
async def list_customer_research(
    services: Services,
    pagination: Pagination,
    filters: Annotated[CustomerResearchListFilter, Depends(_customer_research_filters)],
) -> PaginatedResponse[CustomerResearchRead]:
    return await services.customer_research.list_research(filters, pagination)


@router.post(
    "/generate",
    response_model=CustomerResearchBatchResult,
    status_code=status.HTTP_201_CREATED,
    summary="Batch generate customer research",
)
async def generate_customer_research_batch(
    services: Services,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    force: Annotated[bool, Query(description="Re-research even if current exists")] = False,
) -> CustomerResearchBatchResult:
    return await services.customer_research.research_pending(limit=limit, force=force)


@router.get(
    "/opportunities/{opportunity_id}/current",
    response_model=CustomerResearchDetail,
    summary="Get current customer research",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Customer research not found"}},
)
async def get_current_customer_research(
    opportunity_id: UUID,
    services: Services,
) -> CustomerResearchDetail:
    return await services.customer_research.get_current_research(opportunity_id)


@router.get(
    "/opportunities/{opportunity_id}/history",
    response_model=list[CustomerResearchRead],
    summary="List customer research history",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def list_customer_research_history(
    opportunity_id: UUID,
    services: Services,
) -> list[CustomerResearchRead]:
    return await services.customer_research.list_history(opportunity_id)


@router.post(
    "/opportunities/{opportunity_id}/generate",
    response_model=CustomerResearchResult,
    status_code=status.HTTP_201_CREATED,
    summary="Generate customer research for opportunity",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Opportunity not found"}},
)
async def generate_customer_research(
    opportunity_id: UUID,
    services: Services,
    force: Annotated[bool, Query(description="Re-research even if current exists")] = False,
) -> CustomerResearchResult:
    return await services.customer_research.research_opportunity(opportunity_id, force=force)


@router.get(
    "/{research_id}",
    response_model=CustomerResearchDetail,
    summary="Get customer research run",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Customer research not found"}},
)
async def get_customer_research(research_id: UUID, services: Services) -> CustomerResearchDetail:
    return await services.customer_research.get_research(research_id)
