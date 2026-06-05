"""Tests for market research LangGraph retry and validation flow."""

from uuid import uuid4

import pytest

from app.agents.market_research.graph import MarketResearchAgent
from app.agents.market_research.mock_client import (
    MockMarketResearchLLMClient,
    default_mock_research_output,
    invalid_hierarchy_research_output,
)
from app.agents.market_research.schemas import OpportunityResearchContext
from app.config import Settings


def _context() -> OpportunityResearchContext:
    return OpportunityResearchContext(
        opportunity_id=uuid4(),
        title="Streamlined DevOps Workflow Management",
        problem_statement="Developers struggle with disjointed project management.",
        target_user="Developers and DevOps teams",
        frequency_signal="Multiple complaints mention workflow friction.",
        existing_alternatives="Docker, Github",
        gap="No integrated workflow tool.",
        confidence_score=0.8,
        domain_codes=["devtools"],
        category_codes=["workflow"],
        persona_codes=["developer"],
        complaint_summaries=["Deploy pipeline breaks on step three."],
    )


@pytest.mark.asyncio
async def test_retry_passes_validation_errors_to_llm() -> None:
    mock = MockMarketResearchLLMClient(
        [invalid_hierarchy_research_output(), default_mock_research_output()]
    )
    settings = Settings(
        api_key="test-api-key-for-market-graph",
        research_model="mock-research",
        research_max_retries=2,
    )
    agent = MarketResearchAgent(mock, settings)

    result = await agent.run(_context())

    assert result.status == "completed"
    assert mock.call_count == 2
    assert mock.last_validation_errors is not None
    assert any("tam_usd must not exceed market_size_usd" in err for err in mock.last_validation_errors)


@pytest.mark.asyncio
async def test_graph_succeeds_after_retry_correction() -> None:
    mock = MockMarketResearchLLMClient(
        [invalid_hierarchy_research_output(), default_mock_research_output()]
    )
    settings = Settings(
        api_key="test-api-key-for-market-graph",
        research_model="mock-research",
        research_max_retries=2,
    )
    agent = MarketResearchAgent(mock, settings)

    result = await agent.run(_context())

    assert result.status == "completed"
    assert result.draft is not None
    assert result.draft.tam_usd <= result.draft.market_size_usd
    assert result.draft.sam_usd <= result.draft.tam_usd
