"""Tests for customer research quote grounding and canonicalization."""

from uuid import uuid4

import pytest

from app.agents.customer_research.grounding import (
    canonicalize_representative_complaints,
    normalize_complaint_indices,
    representative_quote_grounded,
)
from app.agents.customer_research.mock_client import default_mock_customer_research_output
from app.agents.customer_research.schemas import (
    ComplaintEvidenceItem,
    CustomerResearchLLMOutput,
    OpportunityCustomerContext,
    RepresentativeComplaintOutput,
    SupportingEvidenceOutput,
)
from app.agents.customer_research.validator import (
    CustomerResearchValidationError,
    CustomerResearchValidator,
)


def _evidence_item(
    *,
    index: int,
    quote: str,
    summary: str = "Sample complaint summary for testing.",
) -> ComplaintEvidenceItem:
    return ComplaintEvidenceItem(
        index=index,
        complaint_id=uuid4(),
        signal_id=uuid4(),
        summary=summary,
        verbatim_quote=quote,
        severity=4,
        source_type="discussion",
        source_name="hn-test",
        url=f"https://example.com/{index}",
    )


def _context(*items: ComplaintEvidenceItem) -> OpportunityCustomerContext:
    return OpportunityCustomerContext(
        opportunity_id=uuid4(),
        title="Dev workflow tool",
        problem_statement="Developers struggle with environment setup.",
        target_user="Software engineers",
        frequency_signal="Repeated complaints",
        gap="No unified workflow",
        confidence_score=0.8,
        complaint_evidence=list(items),
    )


def test_representative_quote_grounded_with_html_entities() -> None:
    stored = "We can&#x27;t deploy without fixing libraries."
    generated = "We can't deploy without fixing libraries."
    assert representative_quote_grounded(generated=generated, evidence_quote=stored)


def test_representative_quote_rejects_hallucination() -> None:
    evidence = "Real complaint about npm install pain."
    assert not representative_quote_grounded(
        generated="This quote never appeared in evidence.",
        evidence_quote=evidence,
    )


def test_canonicalize_replaces_ungrounded_quote_when_index_valid() -> None:
    evidence_quote = "I am frustrated with dependency sprawl every sprint."
    ctx = _context(_evidence_item(index=0, quote=evidence_quote))
    output = CustomerResearchLLMOutput(
        pain_score=70,
        urgency_score=65,
        frequency_score=60,
        customer_sentiment="negative",
        sentiment_score=-0.5,
        cares_verdict="yes",
        representative_complaints=[
            RepresentativeComplaintOutput(
                summary="Paraphrased frustration about dependencies.",
                verbatim_quote="Users hate dependency management complexity.",
                severity=3,
                source_type="discussion",
                complaint_index=0,
            )
        ],
        supporting_evidence=[
            SupportingEvidenceOutput(
                evidence_type="discussion",
                excerpt="Dependency sprawl mentioned repeatedly.",
                source_reference="HN thread",
                supports_conclusion="pain",
                confidence="high",
                complaint_index=0,
            )
        ],
        executive_summary=(
            "Customers express sustained frustration with dependency and environment "
            "management overhead across multiple discussion threads."
        ),
    )

    fixed = canonicalize_representative_complaints(output, ctx)
    assert fixed.representative_complaints[0].verbatim_quote == evidence_quote
    assert fixed.representative_complaints[0].severity == 4

    validator = CustomerResearchValidator()
    result = validator.validate(fixed, context=ctx)
    assert result.representative_complaints[0].verbatim_quote == evidence_quote


def test_validator_accepts_normalized_quote_without_canonicalization() -> None:
    stored = "See path foo&#x2F;bar in config and rage quit."
    generated = "See path foo/bar in config"
    ctx = _context(_evidence_item(index=0, quote=stored))
    output = default_mock_customer_research_output()
    output.representative_complaints = [
        RepresentativeComplaintOutput(
            summary="Config path frustration.",
            verbatim_quote=generated,
            severity=4,
            source_type="discussion",
            complaint_index=0,
        )
    ]
    output.supporting_evidence[0].complaint_index = 0
    output.supporting_evidence[0].excerpt = generated

    result = CustomerResearchValidator().validate(output, context=ctx)
    assert result.representative_complaints[0].verbatim_quote == generated


def test_normalize_singleton_complaint_index_coerces_uuid_prefix() -> None:
    ctx = _context(_evidence_item(index=0, quote="Stripe chargeback fees are unfair."))
    output = default_mock_customer_research_output()
    output.representative_complaints[0].complaint_index = 926
    output.supporting_evidence[0].complaint_index = 926

    normalized = normalize_complaint_indices(output, ctx)
    assert normalized.representative_complaints[0].complaint_index == 0
    assert normalized.supporting_evidence[0].complaint_index == 0

    result = CustomerResearchValidator().validate(normalized, context=ctx)
    assert result.representative_complaints[0].complaint_index == 0


def test_normalize_does_not_coerce_indices_for_multi_complaint_opportunity() -> None:
    ctx = _context(
        _evidence_item(index=0, quote="First evidence quote."),
        _evidence_item(index=1, quote="Second evidence quote."),
    )
    output = default_mock_customer_research_output()
    output.representative_complaints[0].complaint_index = 5

    normalized = normalize_complaint_indices(output, ctx)
    assert normalized.representative_complaints[0].complaint_index == 5

    with pytest.raises(CustomerResearchValidationError) as exc_info:
        CustomerResearchValidator().validate(normalized, context=ctx)
    assert any("out of range" in err for err in exc_info.value.errors)


def test_validator_rejects_missing_complaint_index_when_evidence_provided() -> None:
    ctx = _context(_evidence_item(index=0, quote="Real quote from HN."))
    output = default_mock_customer_research_output()
    output.representative_complaints = [
        RepresentativeComplaintOutput(
            summary="Summary without index.",
            verbatim_quote="Real quote from HN.",
            severity=4,
            source_type="discussion",
            complaint_index=None,
        )
    ]

    with pytest.raises(CustomerResearchValidationError) as exc_info:
        CustomerResearchValidator().validate(output, context=ctx)
    assert any("complaint_index is required" in err for err in exc_info.value.errors)


def test_validator_rejects_out_of_range_complaint_index() -> None:
    ctx = _context(
        _evidence_item(index=0, quote="First evidence quote."),
        _evidence_item(index=1, quote="Second evidence quote."),
    )
    output = default_mock_customer_research_output()
    output.representative_complaints[0].complaint_index = 3

    with pytest.raises(CustomerResearchValidationError) as exc_info:
        CustomerResearchValidator().validate(output, context=ctx)
    assert any("out of range" in err for err in exc_info.value.errors)


def test_validator_rejects_ungrounded_quote_without_valid_index() -> None:
    ctx = _context(
        _evidence_item(index=0, quote="First evidence quote."),
        _evidence_item(index=1, quote="Second evidence quote."),
    )
    output = default_mock_customer_research_output()
    output.representative_complaints = [
        RepresentativeComplaintOutput(
            summary="Hallucinated selection.",
            verbatim_quote="Quote that matches neither complaint.",
            severity=4,
            source_type="discussion",
            complaint_index=None,
        )
    ]

    with pytest.raises(CustomerResearchValidationError) as exc_info:
        CustomerResearchValidator().validate(output, context=ctx)
    assert any("complaint_index is required" in err for err in exc_info.value.errors)
