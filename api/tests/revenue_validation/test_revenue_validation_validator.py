"""Unit tests for revenue validation validator."""

from uuid import uuid4

import pytest

from app.agents.revenue_validation.metrics import compute_evaluation_metrics
from app.agents.revenue_validation.mock_client import default_mock_revenue_validation_output
from app.agents.revenue_validation.schemas import (
    CompetitorPricingContext,
    ComplaintEvidenceItem,
    OpportunityRevenueContext,
)
from app.agents.revenue_validation.validator import (
    RevenueValidationError,
    RevenueValidationValidator,
)

QUOTE = "Staff scheduling breaks every week when employees swap shifts without notice."


def _context(*, with_competitors: bool = False) -> OpportunityRevenueContext:
    complaint_id = uuid4()
    signal_id = uuid4()
    competitor_pricing: list[CompetitorPricingContext] = []
    if with_competitors:
        competitor_pricing = [
            CompetitorPricingContext(
                index=0,
                competitor_profile_id=uuid4(),
                name="ShiftApp",
                pricing_model={"model_type": "subscription", "starting_price_usd": 8},
                positioning="Workforce scheduling for hourly teams",
            )
        ]

    return OpportunityRevenueContext(
        opportunity_id=uuid4(),
        title="Staff Scheduling SaaS",
        problem_statement="Ops teams struggle with hourly staff scheduling.",
        target_user="Ops admins",
        existing_alternatives="ShiftApp and spreadsheets",
        gap="No lightweight scheduling workflow.",
        confidence_score=0.86,
        complaint_evidence=[
            ComplaintEvidenceItem(
                index=0,
                complaint_id=complaint_id,
                signal_id=signal_id,
                summary="Staff scheduling chaos from last-minute shift changes.",
                verbatim_quote=QUOTE,
                severity=4,
                product_mentions=["ShiftApp"],
            )
        ],
        competitor_pricing=competitor_pricing,
    )


def test_validator_accepts_valid_output_without_competitors() -> None:
    validator = RevenueValidationValidator()
    output = default_mock_revenue_validation_output(include_competitor_pricing=False)
    result = validator.validate(output, context=_context())
    assert result.willingness_to_pay_score == 74


def test_validator_accepts_valid_output_with_competitors() -> None:
    validator = RevenueValidationValidator()
    output = default_mock_revenue_validation_output(include_competitor_pricing=True)
    result = validator.validate(output, context=_context(with_competitors=True))
    assert result.revenue_confidence_score == 68


def test_validator_requires_competitor_pricing_evidence() -> None:
    validator = RevenueValidationValidator()
    output = default_mock_revenue_validation_output(include_competitor_pricing=False)
    with pytest.raises(RevenueValidationError) as exc_info:
        validator.validate(output, context=_context(with_competitors=True))
    assert any("competitor_pricing" in error for error in exc_info.value.errors)


def test_validator_rejects_inconsistent_scores() -> None:
    validator = RevenueValidationValidator()
    output = default_mock_revenue_validation_output(include_competitor_pricing=False)
    output.willingness_to_pay_score = 85
    output.revenue_confidence_score = 10
    with pytest.raises(RevenueValidationError) as exc_info:
        validator.validate(output, context=_context())
    assert any("revenue_confidence_score" in error for error in exc_info.value.errors)


def test_evaluation_metrics_include_readiness_score() -> None:
    output = default_mock_revenue_validation_output(include_competitor_pricing=False)
    metrics = compute_evaluation_metrics(output)
    assert metrics["willingness_to_pay_score"] == 74
    assert metrics["evaluation_readiness_score"] > 0
