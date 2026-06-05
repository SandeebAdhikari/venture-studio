"""Unit tests for opportunity synthesis validation."""

from uuid import uuid4

import pytest

from app.agents.opportunity.schemas import ComplaintEvidence, OpportunityLLMOutput
from app.agents.opportunity.validator import OpportunityValidationError, OpportunityValidator


def _evidence(*, summary: str, products: list[str] | None = None) -> ComplaintEvidence:
    return ComplaintEvidence(
        id=uuid4(),
        summary=summary,
        verbatim_quote=summary,
        severity=4,
        domain_code="saas_b2b",
        category_code="workflow",
        persona_code="ops_admin",
        product_mentions=products or [],
    )


def _output(**overrides) -> OpportunityLLMOutput:
    payload = {
        "title": "Staff Scheduling SaaS",
        "problem_statement": "Teams struggle to coordinate staff scheduling across locations.",
        "target_user": "Ops admins managing hourly staff",
        "frequency_signal": "Multiple complaints mention staff scheduling friction.",
        "existing_alternatives": "Teams mention ShiftApp and spreadsheets in the evidence.",
        "gap": "No purpose-built scheduling workflow for shift-based teams.",
        "confidence_score": 0.82,
        "explanation": "Recurring staff scheduling complaints indicate a focused SaaS wedge.",
    }
    payload.update(overrides)
    return OpportunityLLMOutput(**payload)


def test_validator_accepts_grounded_output() -> None:
    evidence = [
        _evidence(
            summary="Staff scheduling breaks when shifts change.",
            products=["ShiftApp"],
        )
    ]
    validated = OpportunityValidator().validate(
        _output(),
        evidence=evidence,
        topic="Staff Scheduling",
    )
    assert validated.title == "Staff Scheduling SaaS"


def test_validator_rejects_ungrounded_product() -> None:
    evidence = [_evidence(summary="Staff scheduling breaks when shifts change.")]
    with pytest.raises(OpportunityValidationError) as exc:
        OpportunityValidator().validate(
            _output(existing_alternatives="Teams rely on MegaCorp Scheduler Pro."),
            evidence=evidence,
            topic="Staff Scheduling",
        )
    assert any("ungrounded product" in err for err in exc.value.errors)


def test_validator_ignores_none_mentioned_phrasing() -> None:
    evidence = [_evidence(summary="Staff scheduling breaks when shifts change.")]
    validated = OpportunityValidator().validate(
        _output(existing_alternatives="None mentioned in the complaints."),
        evidence=evidence,
        topic="Staff Scheduling",
    )
    assert validated.title == "Staff Scheduling SaaS"


def test_validator_ignores_na_product_tokens() -> None:
    evidence = [_evidence(summary="Staff scheduling breaks when shifts change.")]
    validated = OpportunityValidator().validate(
        _output(existing_alternatives="No named products in evidence (N/A)."),
        evidence=evidence,
        topic="Staff Scheduling",
    )
    assert "N/A" not in OpportunityValidator._extract_product_candidates(
        validated.existing_alternatives
    )


def test_validator_accepts_topic_via_taxonomy_when_display_topic_cosmetic() -> None:
    evidence = [
        _evidence(
            summary="Developers struggle with deployment environment drift.",
            products=[],
        )
    ]
    validated = OpportunityValidator().validate(
        _output(
            title="Workflow Devtools Opportunity",
            existing_alternatives="No named products in evidence",
        ),
        evidence=evidence,
        topic="Don T",
        anchor_phrase="don t",
        domain_code="devtools",
        category_code="workflow",
    )
    assert validated.title.startswith("Workflow")


def test_validator_bypasses_topic_reflection_for_founder_signal_patterns() -> None:
    evidence = [
        _evidence(
            summary="The user seeks affordable payment processing alternatives in the EU.",
            products=["Stripe", "PayPal"],
        )
    ]
    validated = OpportunityValidator().validate(
        _output(
            title="Affordable Payment Processing for Founders",
            problem_statement=(
                "Founders struggle with high upfront payment processing costs and limited "
                "regional processor options for recurring billing."
            ),
            existing_alternatives="Stripe and PayPal appear in the evidence.",
            explanation="Recurring processor access complaints indicate a focused SaaS wedge.",
        ),
        evidence=evidence,
        topic="Payment Processor — Accept Payments",
        anchor_phrase="payment_processor|accept_payments",
        domain_code="fintech",
        category_code="pricing",
        pattern_source="founder_signal_clustering",
    )
    assert validated.title == "Affordable Payment Processing for Founders"


def test_validator_still_enforces_product_grounding_for_founder_signal_patterns() -> None:
    evidence = [_evidence(summary="Payment processing costs are too high.", products=["Stripe"])]
    with pytest.raises(OpportunityValidationError) as exc:
        OpportunityValidator().validate(
            _output(existing_alternatives="Teams rely on MegaCorp Billing Pro."),
            evidence=evidence,
            topic="Payment Processor — Accept Payments",
            anchor_phrase="payment_processor|accept_payments",
            pattern_source="founder_signal_clustering",
        )
    assert any("ungrounded product" in err for err in exc.value.errors)


def test_validator_rejects_cosmetic_topic_without_taxonomy_or_anchor_match() -> None:
    evidence = [_evidence(summary="Unrelated product pricing complaints only.")]
    with pytest.raises(OpportunityValidationError) as exc:
        OpportunityValidator().validate(
            _output(
                title="Generic SaaS Tool",
                existing_alternatives="No named products in evidence",
            ),
            evidence=evidence,
            topic="Don T",
            anchor_phrase="don t",
            domain_code="devtools",
            category_code="workflow",
        )
    assert any("topic not reflected" in err for err in exc.value.errors)
