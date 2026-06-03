"""LLM budget REST endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import Services
from app.schemas.budget import BudgetHistoryResponse, BudgetStatusResponse

router = APIRouter(prefix="/budget", tags=["budget"])


@router.get(
    "",
    response_model=BudgetStatusResponse,
    summary="Current daily LLM budget status",
    description="Daily spend, per-agent usage, remaining budget, and threshold warnings.",
)
async def get_budget_status(services: Services) -> BudgetStatusResponse:
    status = await services.llm_budget.get_status()
    return BudgetStatusResponse.model_validate(status)


@router.get(
    "/history",
    response_model=BudgetHistoryResponse,
    summary="Historical daily LLM budget usage",
)
async def get_budget_history(
    services: Services,
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> BudgetHistoryResponse:
    from datetime import UTC, datetime

    items = await services.llm_budget.get_history(days=days)
    return BudgetHistoryResponse(
        generated_at=datetime.now(UTC),
        days=days,
        items=items,
    )
