"""Unit tests for competitor analysis validator."""

import pytest

from app.agents.competitor_intelligence.mock_client import default_mock_competitor_output
from app.agents.competitor_intelligence.schemas import OpportunityCompetitorContext
from app.agents.competitor_intelligence.validator import (
    CompetitorAnalysisValidator,
    CompetitorValidationError,
)
from uuid import uuid4


def _context(**kwargs) -> OpportunityCompetitorContext:
    defaults = {
        "opportunity_id": uuid4(),
        "title": "Staff Scheduling SaaS",
        "problem_statement": "Ops teams struggle with hourly staff scheduling.",
        "target_user": "Ops admins",
        "existing_alternatives": "Teams mention ShiftApp and spreadsheets.",
        "gap": "No lightweight scheduling workflow.",
        "confidence_score": 0.86,
        "known_products": ["ShiftApp"],
        "complaint_summaries": ["Staff scheduling breaks every week."],
        "product_mentions": ["ShiftApp"],
    }
    defaults.update(kwargs)
    return OpportunityCompetitorContext(**defaults)


def test_validator_accepts_valid_output() -> None:
    validator = CompetitorAnalysisValidator()
    result = validator.validate(default_mock_competitor_output(), context=_context())
    assert len(result.competitors) == 2


def test_validator_rejects_inconsistent_sentiment_score() -> None:
    validator = CompetitorAnalysisValidator()
    output = default_mock_competitor_output()
    output.competitors[0].review_sentiment = "positive"
    output.competitors[0].sentiment_score = -0.8
    with pytest.raises(CompetitorValidationError) as exc_info:
        validator.validate(output, context=_context())
    assert any("sentiment_score inconsistent" in error for error in exc_info.value.errors)


def test_validator_requires_evidence_grounding_when_products_known() -> None:
    validator = CompetitorAnalysisValidator()
    output = default_mock_competitor_output()
    output.competitors[0].name = "UnknownToolXYZ"
    output.competitors[1].name = "AnotherUnknownABC"
    with pytest.raises(CompetitorValidationError) as exc_info:
        validator.validate(output, context=_context())
    assert any("grounded in opportunity evidence" in error for error in exc_info.value.errors)
