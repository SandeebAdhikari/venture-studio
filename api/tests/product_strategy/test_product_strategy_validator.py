"""Unit tests for product strategy validator and roadmap generation."""

from uuid import uuid4

import pytest

from app.agents.product_strategy.metrics import compute_planning_metrics, generate_roadmap
from app.agents.product_strategy.mock_client import default_mock_product_strategy_output
from app.agents.product_strategy.schemas import ComplaintEvidenceItem, OpportunityPlanningContext
from app.agents.product_strategy.validator import (
    ProductStrategyValidationError,
    ProductStrategyValidator,
)

QUOTE = "Staff scheduling breaks every week when employees swap shifts without notice."


def _context() -> OpportunityPlanningContext:
    complaint_id = uuid4()
    signal_id = uuid4()
    return OpportunityPlanningContext(
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
    validator = ProductStrategyValidator()
    output = default_mock_product_strategy_output()
    result = validator.validate(output, context=_context())
    assert "shift swap" in result.mvp_definition.lower()


def test_validator_rejects_unknown_priority_feature() -> None:
    validator = ProductStrategyValidator()
    output = default_mock_product_strategy_output()
    output.feature_priorities[0].feature_name = "Unknown feature"
    with pytest.raises(ProductStrategyValidationError) as exc_info:
        validator.validate(output, context=_context())
    assert any("unknown features" in error for error in exc_info.value.errors)


def test_validator_rejects_timeline_shorter_than_phases() -> None:
    validator = ProductStrategyValidator()
    output = default_mock_product_strategy_output()
    output.estimated_timeline.total_weeks = 2
    with pytest.raises(ProductStrategyValidationError) as exc_info:
        validator.validate(output, context=_context())
    assert any("total_weeks" in error for error in exc_info.value.errors)


def test_generate_roadmap_builds_sequential_phases() -> None:
    output = default_mock_product_strategy_output()
    roadmap = generate_roadmap(output.development_phases, output.estimated_timeline)
    assert len(roadmap) == 3
    assert roadmap[0]["start_week"] == 1
    assert roadmap[0]["end_week"] == 6
    assert roadmap[1]["start_week"] == 7
    assert roadmap[2]["end_week"] == 13


def test_planning_metrics_include_readiness_score() -> None:
    output = default_mock_product_strategy_output()
    roadmap = generate_roadmap(output.development_phases, output.estimated_timeline)
    metrics = compute_planning_metrics(output, roadmap=roadmap)
    assert metrics["core_feature_count"] == 3
    assert metrics["roadmap_item_count"] == 3
    assert metrics["planning_readiness_score"] > 0
