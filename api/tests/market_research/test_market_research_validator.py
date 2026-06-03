"""Unit tests for market research validator."""

import pytest

from app.agents.market_research.mock_client import default_mock_research_output
from app.agents.market_research.schemas import CustomerSegment, MarketResearchLLMOutput
from app.agents.market_research.validator import (
    MarketResearchValidationError,
    MarketResearchValidator,
)


def _valid_output() -> MarketResearchLLMOutput:
    return default_mock_research_output()


def test_validator_accepts_valid_output() -> None:
    validator = MarketResearchValidator()
    result = validator.validate(_valid_output())
    assert result.tam_usd == pytest.approx(4_500_000_000)


def test_validator_rejects_sam_greater_than_tam() -> None:
    validator = MarketResearchValidator()
    output = _valid_output().model_copy(update={"sam_usd": 5_000_000_000})
    with pytest.raises(MarketResearchValidationError) as exc_info:
        validator.validate(output)
    assert "sam_usd must not exceed tam_usd" in exc_info.value.errors


def test_validator_rejects_tam_greater_than_market_size() -> None:
    validator = MarketResearchValidator()
    output = _valid_output().model_copy(update={"tam_usd": 15_000_000_000})
    with pytest.raises(MarketResearchValidationError) as exc_info:
        validator.validate(output)
    assert "tam_usd must not exceed market_size_usd" in exc_info.value.errors


def test_validator_rejects_empty_segments() -> None:
    validator = MarketResearchValidator()
    output = _valid_output().model_copy(update={"customer_segments": []})
    with pytest.raises(MarketResearchValidationError) as exc_info:
        validator.validate(output)
    assert "customer_segments must not be empty" in exc_info.value.errors


def test_validator_rejects_short_segment_description() -> None:
    validator = MarketResearchValidator()
    output = _valid_output().model_copy(
        update={
            "customer_segments": [
                CustomerSegment(name="Retail", description="Short", estimated_share_pct=10.0)
            ]
        }
    )
    with pytest.raises(MarketResearchValidationError) as exc_info:
        validator.validate(output)
    assert any("description is too short" in error for error in exc_info.value.errors)
