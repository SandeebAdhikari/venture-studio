"""Tests for market research LLM client prompt and retry feedback."""

from app.agents.market_research.llm_client import market_research_system_prompt


def test_system_prompt_requires_market_sizing_hierarchy() -> None:
    prompt = market_research_system_prompt()
    assert "market_size_usd >= tam_usd >= sam_usd" in prompt
    assert "broadest" in prompt.lower()
    assert "total addressable market" in prompt.lower()
    assert "serviceable addressable market" in prompt.lower()
    assert "fail validation" in prompt.lower()
