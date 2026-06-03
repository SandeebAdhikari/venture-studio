"""API tests for LLM budget endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories import get_repositories


@pytest.fixture(autouse=True)
def _budget_settings(monkeypatch):
    monkeypatch.setenv("LLM_DAILY_BUDGET_USD", "2.0")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_get_budget_status(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    repos = get_repositories(db_session)
    await repos.llm_calls.log_agent_call(
        entity_type="signal",
        entity_id=uuid4(),
        graph_name="classify_complaint",
        model="gpt-4o-mini",
        attempt=1,
        prompt_tokens=500,
        completion_tokens=100,
        estimated_cost_usd=0.05,
        latency_ms=50,
        cost_usd=0.05,
        status="success",
        error_detail=None,
        eval_metadata={},
    )

    response = await client.get("/api/v1/budget", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["budget_usd"] == 2.0
    assert payload["spent_usd"] == pytest.approx(0.05)
    assert payload["enabled"] is True
    assert len(payload["by_agent"]) == 1
    assert payload["by_agent"][0]["graph_name"] == "classify_complaint"


@pytest.mark.asyncio
async def test_get_budget_history(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    repos = get_repositories(db_session)
    await repos.llm_calls.log_agent_call(
        entity_type="signal",
        entity_id=uuid4(),
        graph_name="research_market",
        model="gpt-4o-mini",
        attempt=1,
        prompt_tokens=800,
        completion_tokens=200,
        estimated_cost_usd=0.08,
        latency_ms=80,
        cost_usd=0.08,
        status="success",
        error_detail=None,
        eval_metadata={},
    )

    response = await client.get("/api/v1/budget/history?days=7", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["days"] == 7
    assert len(payload["items"]) >= 1
    assert payload["items"][0]["spent_usd"] == pytest.approx(0.08)
