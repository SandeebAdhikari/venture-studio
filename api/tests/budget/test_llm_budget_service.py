"""Integration tests for LLM budget service."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.exceptions import BudgetExceededError
from app.repositories import get_repositories
from app.services.llm_budget import LLMBudgetService


@pytest.fixture
def budget_settings() -> Settings:
    return Settings(api_key="budget-test-key-16chars", llm_daily_budget_usd=0.001)


async def _insert_call(
    db_session: AsyncSession,
    *,
    graph_name: str = "classify_complaint",
    cost_usd: float = 0.10,
    estimated_cost_usd: float | None = None,
    created_at: datetime | None = None,
) -> None:
    repos = get_repositories(db_session)
    call = await repos.llm_calls.log_agent_call(
        entity_type="signal",
        entity_id=uuid4(),
        graph_name=graph_name,
        model="gpt-4o-mini",
        attempt=1,
        prompt_tokens=1000,
        completion_tokens=200,
        estimated_cost_usd=estimated_cost_usd if estimated_cost_usd is not None else cost_usd,
        latency_ms=100,
        cost_usd=cost_usd,
        status="success",
        error_detail=None,
        eval_metadata={},
    )
    if created_at is not None:
        from sqlalchemy import update

        from app.db.models.llm_call import LLMCall

        await db_session.execute(
            update(LLMCall).where(LLMCall.id == call.id).values(created_at=created_at)
        )
    await db_session.flush()


@pytest.mark.asyncio
async def test_daily_usage_and_by_agent(db_session: AsyncSession, budget_settings: Settings):
    await _insert_call(db_session, graph_name="classify_complaint", cost_usd=0.20)
    await _insert_call(db_session, graph_name="research_market", cost_usd=0.30)

    budget = LLMBudgetService(get_repositories(db_session), budget_settings)
    status = await budget.get_status()

    assert status["budget_usd"] == 0.001
    assert status["spent_usd"] == pytest.approx(0.50)
    assert status["remaining_usd"] == pytest.approx(0.0)
    assert status["utilization_pct"] > 100
    assert status["calls_total"] == 2
    assert len(status["by_agent"]) == 2
    assert status["warnings"][0]["triggered"] is True


@pytest.mark.asyncio
async def test_assert_can_spend_blocks_when_budget_exceeded(
    db_session: AsyncSession,
    budget_settings: Settings,
):
    await _insert_call(db_session, cost_usd=0.0008)

    budget = LLMBudgetService(get_repositories(db_session), budget_settings)
    estimated = budget.estimate_request_cost("classify_complaint", "gpt-4o-mini")

    with pytest.raises(BudgetExceededError):
        await budget.assert_can_spend(estimated, "classify_complaint")


@pytest.mark.asyncio
async def test_try_prepare_call_returns_block_reason(
    db_session: AsyncSession,
    budget_settings: Settings,
):
    await _insert_call(db_session, cost_usd=0.0009)

    budget = LLMBudgetService(get_repositories(db_session), budget_settings)
    estimated, block_reason = await budget.try_prepare_call("classify_complaint", "gpt-4o-mini")

    assert estimated > 0
    assert block_reason is not None
    assert block_reason.startswith("budget_exceeded:")


@pytest.mark.asyncio
async def test_threshold_alerts_recorded(db_session: AsyncSession):
    settings = Settings(api_key="budget-test-key-16chars", llm_daily_budget_usd=1.0)
    await _insert_call(db_session, cost_usd=0.55)

    budget = LLMBudgetService(get_repositories(db_session), settings)
    await budget.after_call_recorded()

    alerts = await budget._metrics.list_alerts_for_day(budget._metrics.utc_today())
    triggered = {alert.threshold_pct for alert in alerts}
    assert 50 in triggered
    assert 75 not in triggered
    assert 90 not in triggered


@pytest.mark.asyncio
async def test_history_groups_by_day(db_session: AsyncSession, budget_settings: Settings):
    yesterday = datetime.now(UTC) - timedelta(days=1)
    await _insert_call(db_session, cost_usd=0.25, created_at=yesterday)
    await _insert_call(db_session, cost_usd=0.15)

    budget = LLMBudgetService(get_repositories(db_session), budget_settings)
    history = await budget.get_history(days=7)

    assert len(history) >= 2
    assert history[0]["actual_cost_usd_total"] >= 0.15


@pytest.mark.asyncio
async def test_disabled_budget_when_limit_zero(db_session: AsyncSession):
    settings = Settings(api_key="budget-test-key-16chars", llm_daily_budget_usd=0)
    budget = LLMBudgetService(get_repositories(db_session), settings)

    assert budget.enabled is False
    estimated, block_reason = await budget.try_prepare_call("classify_complaint", "gpt-4o-mini")
    assert estimated == 0.0
    assert block_reason is None
