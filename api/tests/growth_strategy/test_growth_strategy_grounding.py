"""Tests for growth strategy evidence index grounding."""

from uuid import uuid4

import pytest

from app.agents.growth_strategy.grounding import normalize_evidence_indices
from app.agents.growth_strategy.mock_client import default_mock_growth_strategy_output
from app.agents.growth_strategy.schemas import ComplaintEvidenceItem, OpportunityGrowthContext
from app.agents.growth_strategy.validator import (
    GrowthStrategyValidationError,
    GrowthStrategyValidator,
)

QUOTE = "Staff scheduling breaks every week when employees swap shifts without notice."


def _complaint(*, index: int = 0) -> ComplaintEvidenceItem:
    return ComplaintEvidenceItem(
        index=index,
        complaint_id=uuid4(),
        signal_id=uuid4(),
        summary="Staff scheduling chaos from last-minute shift changes.",
        verbatim_quote=QUOTE if index == 0 else f"Quote for complaint {index}.",
        severity=4,
        product_mentions=["ShiftApp"],
    )


def _context(*complaints: ComplaintEvidenceItem) -> OpportunityGrowthContext:
    return OpportunityGrowthContext(
        opportunity_id=uuid4(),
        title="Staff Scheduling SaaS",
        problem_statement="Ops teams struggle with hourly staff scheduling.",
        target_user="Ops admins",
        frequency_signal="Repeated scheduling complaints.",
        existing_alternatives="ShiftApp and spreadsheets",
        gap="No lightweight scheduling workflow.",
        confidence_score=0.86,
        complaint_evidence=list(complaints),
    )


def test_normalize_singleton_complaint_index_coerces_uuid_prefix() -> None:
    ctx = _context(_complaint())
    output = default_mock_growth_strategy_output()
    output.supporting_evidence[0].complaint_index = 926
    output.supporting_evidence[1].complaint_index = 37

    normalized = normalize_evidence_indices(output, ctx)
    assert normalized.supporting_evidence[0].complaint_index == 0
    assert normalized.supporting_evidence[1].complaint_index == 0

    result = GrowthStrategyValidator().validate(normalized, context=ctx)
    assert result.supporting_evidence[0].complaint_index == 0


def test_normalize_leaves_valid_singleton_index_unchanged() -> None:
    ctx = _context(_complaint())
    output = default_mock_growth_strategy_output()

    normalized = normalize_evidence_indices(output, ctx)
    assert normalized.supporting_evidence[0].complaint_index == 0

    result = GrowthStrategyValidator().validate(normalized, context=ctx)
    assert result.supporting_evidence[0].complaint_index == 0


def test_normalize_does_not_coerce_indices_for_multi_complaint_opportunity() -> None:
    ctx = _context(_complaint(index=0), _complaint(index=1))
    output = default_mock_growth_strategy_output()
    output.supporting_evidence[0].complaint_index = 5

    normalized = normalize_evidence_indices(output, ctx)
    assert normalized.supporting_evidence[0].complaint_index == 5

    with pytest.raises(GrowthStrategyValidationError) as exc_info:
        GrowthStrategyValidator().validate(normalized, context=ctx)
    assert any("out of range" in err for err in exc_info.value.errors)
