"""Integration test: classification agent respects LLM budget."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.classification.mock_client import MockClassificationLLMClient
from app.agents.classification.service import ComplaintClassificationService
from app.collection.schemas import RawComplaintInput
from app.collection.service import ComplaintCollectionService
from app.config import Settings
from app.db.enums import SourceType
from app.db.models.source import Source
from app.repositories import get_repositories
from app.services.llm_budget import LLMBudgetService


@pytest.fixture
def tight_budget_settings() -> Settings:
    return Settings(
        api_key="budget-agent-test-key16",
        llm_daily_budget_usd=0.0001,
        classification_max_retries=1,
        classification_model="gpt-4o-mini",
    )


@pytest.mark.asyncio
async def test_classification_stops_when_budget_exceeded(
    db_session: AsyncSession,
    tight_budget_settings: Settings,
):
    source = Source(
        name=f"budget-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    collection = ComplaintCollectionService(get_repositories(db_session))
    ingest_result = await collection.ingest(
        source.id,
        RawComplaintInput(
            external_id=f"ext-{uuid4()}",
            title="Budget guard test",
            body="This workflow should stop when the daily LLM budget is exceeded.",
            url="https://example.com/budget",
            author="tester",
        ),
    )
    signal_id = ingest_result.signal_id

    repos = get_repositories(db_session)
    budget = LLMBudgetService(repos, tight_budget_settings)
    service = ComplaintClassificationService(
        repos,
        tight_budget_settings,
        llm_client=MockClassificationLLMClient([], model="gpt-4o-mini"),
        budget_service=budget,
    )

    result = await service.classify_signal(signal_id)
    assert result.status == "failed"
    assert result.error is not None
    assert "budget_exceeded" in result.error

    calls = await repos.llm_calls.list(limit=5)
    assert len(calls) >= 1
    assert calls[0].error_detail is not None
    assert "budget_exceeded" in calls[0].error_detail
