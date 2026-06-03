"""Unit tests for growth strategy validator and roadmap generation."""

from uuid import uuid4

import pytest

from app.agents.growth_strategy.metrics import compute_evaluation_metrics, generate_growth_roadmap
from app.agents.growth_strategy.mock_client import default_mock_growth_strategy_output
from app.agents.growth_strategy.schemas import ComplaintEvidenceItem, OpportunityGrowthContext
from app.agents.growth_strategy.validator import GrowthStrategyValidationError, GrowthStrategyValidator

QUOTE = "Staff scheduling breaks every week when employees swap shifts without notice."


def _context() -> OpportunityGrowthContext:
    complaint_id = uuid4()
    signal_id = uuid4()
    return OpportunityGrowthContext(
        opportunity_id=uuid4(),
        title="Staff Scheduling SaaS",
        problem_statement="Ops teams struggle with hourly staff scheduling.",
        target_user="Ops admins",
        frequency_signal="Repeated scheduling complaints.",
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
    )


def test_validator_accepts_valid_output() -> None:
    validator = GrowthStrategyValidator()
    output = default_mock_growth_strategy_output()
    result = validator.validate(output, context=_context())
    assert result.growth_score == 78


def test_validator_rejects_inconsistent_high_growth_and_risk() -> None:
    validator = GrowthStrategyValidator()
    output = default_mock_growth_strategy_output()
    output.growth_score = 90
    output.risk_score = 90
    with pytest.raises(GrowthStrategyValidationError) as exc_info:
        validator.validate(output, context=_context())
    assert any("risk_score" in error for error in exc_info.value.errors)


def test_generate_growth_roadmap_builds_sequential_phases() -> None:
    output = default_mock_growth_strategy_output()
    roadmap = generate_growth_roadmap(output.growth_phases)
    assert len(roadmap) == 3
    assert roadmap[0]["start_month"] == 1
    assert roadmap[0]["end_month"] == 6
    assert roadmap[2]["end_month"] == 27


def test_evaluation_metrics_include_readiness_score() -> None:
    output = default_mock_growth_strategy_output()
    roadmap = generate_growth_roadmap(output.growth_phases)
    metrics = compute_evaluation_metrics(output, growth_roadmap=roadmap)
    assert metrics["growth_score"] == 78
    assert metrics["scalability_score"] == 71
    assert metrics["growth_readiness_score"] > 0
    assert metrics["growth_roadmap_months"] == 27
