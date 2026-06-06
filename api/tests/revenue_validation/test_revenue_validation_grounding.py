"""Tests for revenue validation evidence index grounding."""

from uuid import uuid4

import pytest

from app.agents.revenue_validation.grounding import normalize_evidence_indices
from app.agents.revenue_validation.mock_client import default_mock_revenue_validation_output
from app.agents.revenue_validation.schemas import (
    ComplaintEvidenceItem,
    CompetitorPricingContext,
    OpportunityRevenueContext,
    RevenueEvidenceOutput,
)
from app.agents.revenue_validation.validator import (
    RevenueValidationError,
    RevenueValidationValidator,
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


def _context(
    *complaints: ComplaintEvidenceItem,
    with_competitors: bool = False,
) -> OpportunityRevenueContext:
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
        complaint_evidence=list(complaints),
        competitor_pricing=competitor_pricing,
    )


def test_normalize_singleton_complaint_index_coerces_uuid_prefix() -> None:
    ctx = _context(_complaint())
    output = default_mock_revenue_validation_output(include_competitor_pricing=False)
    output.supporting_evidence[0].complaint_index = 926
    output.supporting_evidence[1].complaint_index = 37

    normalized = normalize_evidence_indices(output, ctx)
    assert normalized.supporting_evidence[0].complaint_index == 0
    assert normalized.supporting_evidence[1].complaint_index == 0

    result = RevenueValidationValidator().validate(normalized, context=ctx)
    assert result.supporting_evidence[0].complaint_index == 0


def test_normalize_leaves_valid_singleton_index_unchanged() -> None:
    ctx = _context(_complaint())
    output = default_mock_revenue_validation_output(include_competitor_pricing=False)

    normalized = normalize_evidence_indices(output, ctx)
    assert normalized.supporting_evidence[0].complaint_index == 0

    result = RevenueValidationValidator().validate(normalized, context=ctx)
    assert result.supporting_evidence[0].complaint_index == 0


def test_normalize_does_not_coerce_indices_for_multi_complaint_opportunity() -> None:
    ctx = _context(_complaint(index=0), _complaint(index=1))
    output = default_mock_revenue_validation_output(include_competitor_pricing=False)
    output.supporting_evidence[0].complaint_index = 5

    normalized = normalize_evidence_indices(output, ctx)
    assert normalized.supporting_evidence[0].complaint_index == 5

    with pytest.raises(RevenueValidationError) as exc_info:
        RevenueValidationValidator().validate(normalized, context=ctx)
    assert any("out of range" in err for err in exc_info.value.errors)


def test_normalize_singleton_competitor_index_coerces_invalid_value() -> None:
    ctx = _context(_complaint(), with_competitors=True)
    output = default_mock_revenue_validation_output(include_competitor_pricing=True)
    output.supporting_evidence[0].competitor_index = 842

    normalized = normalize_evidence_indices(output, ctx)
    assert normalized.supporting_evidence[0].competitor_index == 0

    result = RevenueValidationValidator().validate(normalized, context=ctx)
    assert result.supporting_evidence[0].competitor_index == 0


def test_normalize_does_not_coerce_competitor_index_when_multiple_competitors() -> None:
    ctx = _context(_complaint())
    ctx = ctx.model_copy(
        update={
            "competitor_pricing": [
                CompetitorPricingContext(
                    index=0,
                    competitor_profile_id=uuid4(),
                    name="ShiftApp",
                    pricing_model={"model_type": "subscription"},
                    positioning="Scheduling",
                ),
                CompetitorPricingContext(
                    index=1,
                    competitor_profile_id=uuid4(),
                    name="WhenIWork",
                    pricing_model={"model_type": "subscription"},
                    positioning="Hourly workforce",
                ),
            ]
        }
    )
    output = default_mock_revenue_validation_output(include_competitor_pricing=False)
    output.supporting_evidence = [
        RevenueEvidenceOutput(
            evidence_type="competitor_pricing",
            excerpt="Competitor pricing anchor for comparison.",
            source_reference="Competitor pricing context",
            supports_conclusion="pricing",
            confidence="high",
            competitor_index=3,
        ),
        RevenueEvidenceOutput(
            evidence_type="existing_spending",
            excerpt="Complaints reference paying for scheduling tools.",
            source_reference="Linked complaint evidence",
            supports_conclusion="willingness_to_pay",
            confidence="medium",
            complaint_index=0,
        ),
        RevenueEvidenceOutput(
            evidence_type="budget_signal",
            excerpt="Ops teams budget for scheduling tools.",
            source_reference="Buyer profile inference",
            supports_conclusion="revenue_confidence",
            confidence="medium",
        ),
        RevenueEvidenceOutput(
            evidence_type="purchase_frequency",
            excerpt="Scheduling tools reviewed during annual planning.",
            source_reference="Typical SMB purchase cycle",
            supports_conclusion="frequency",
            confidence="medium",
        ),
    ]

    normalized = normalize_evidence_indices(output, ctx)
    assert normalized.supporting_evidence[0].competitor_index == 3

    with pytest.raises(RevenueValidationError) as exc_info:
        RevenueValidationValidator().validate(normalized, context=ctx)
    assert any("competitor_index out of range" in err for err in exc_info.value.errors)
