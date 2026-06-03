"""Unit tests for go-to-market validator and roadmap generation."""

from uuid import uuid4

import pytest

from app.agents.go_to_market.metrics import compute_ranking_metrics, generate_acquisition_roadmap
from app.agents.go_to_market.mock_client import default_mock_go_to_market_output
from app.agents.go_to_market.schemas import ComplaintEvidenceItem, OpportunityGTMContext
from app.agents.go_to_market.validator import GoToMarketValidationError, GoToMarketValidator

QUOTE = "Staff scheduling breaks every week when employees swap shifts without notice."


def _context() -> OpportunityGTMContext:
    complaint_id = uuid4()
    signal_id = uuid4()
    return OpportunityGTMContext(
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
    validator = GoToMarketValidator()
    output = default_mock_go_to_market_output()
    result = validator.validate(output, context=_context())
    assert result.confidence_score == 72


def test_validator_rejects_duplicate_channel_names() -> None:
    validator = GoToMarketValidator()
    output = default_mock_go_to_market_output()
    output.acquisition_channels[1].channel_name = output.acquisition_channels[0].channel_name
    with pytest.raises(GoToMarketValidationError) as exc_info:
        validator.validate(output, context=_context())
    assert any("unique channel_name" in error for error in exc_info.value.errors)


def test_generate_acquisition_roadmap_builds_sequential_phases() -> None:
    output = default_mock_go_to_market_output()
    roadmap = generate_acquisition_roadmap(output.acquisition_phases)
    assert len(roadmap) == 3
    assert roadmap[0]["start_week"] == 1
    assert roadmap[0]["end_week"] == 4
    assert roadmap[2]["end_week"] == 16


def test_ranking_metrics_include_readiness_and_cac() -> None:
    output = default_mock_go_to_market_output()
    roadmap = generate_acquisition_roadmap(output.acquisition_phases)
    metrics = compute_ranking_metrics(output, acquisition_roadmap=roadmap)
    assert metrics["estimated_cac_usd"] == 135.0
    assert metrics["confidence_score"] == 72
    assert metrics["gtm_readiness_score"] > 0
    assert metrics["acquisition_roadmap_weeks"] == 16
