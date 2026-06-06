"""Tests for founder signal clustering (Pass 3)."""

from uuid import uuid4

from app.agents.opportunity.founder_signal_clustering import (
    PATTERN_SOURCE_FOUNDER_SIGNAL,
    detect_founder_signal_patterns,
    evaluate_founder_signal_variants,
)
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.taxonomy_fallback import resolve_generation_patterns


def _evidence(
    *,
    business_function_code: str,
    jtbd_code: str,
    consequence_code: str,
    domain_code: str = "fintech",
    category_code: str = "pricing",
    persona_code: str = "founder",
    verbatim_quote: str | None = None,
) -> ComplaintEvidence:
    return ComplaintEvidence(
        id=uuid4(),
        summary="Billing pain summary for founder signal clustering test case.",
        verbatim_quote=verbatim_quote
        or "Processor removed and revenue collection stopped immediately.",
        severity=4,
        domain_code=domain_code,
        category_code=category_code,
        persona_code=persona_code,
        product_mentions=["Stripe"],
        business_function_code=business_function_code,
        jtbd_code=jtbd_code,
        consequence_code=consequence_code,
    )


def test_variant_a_groups_by_business_function() -> None:
    evidence = [
        _evidence(
            business_function_code="payment_processor",
            jtbd_code="accept_payments",
            consequence_code="revenue_interruption",
        )
        for _ in range(3)
    ]
    patterns = detect_founder_signal_patterns(evidence, variant="A", emit_logs=False)
    assert len(patterns) == 1
    assert patterns[0].pattern_source == PATTERN_SOURCE_FOUNDER_SIGNAL
    assert patterns[0].anchor_phrase == "payment_processor"
    assert patterns[0].founder_grouping_variant == "A"
    assert patterns[0].complaint_count == 3


def test_variant_d_requires_full_signal_match() -> None:
    evidence = [
        _evidence(
            business_function_code="fraud_prevention",
            jtbd_code="prevent_fraud",
            consequence_code="fraud_loss",
            domain_code="fintech",
        )
        for _ in range(3)
    ] + [
        _evidence(
            business_function_code="fraud_prevention",
            jtbd_code="prevent_fraud",
            consequence_code="margin_erosion",
            domain_code="saas_b2b",
        )
    ]
    patterns = detect_founder_signal_patterns(evidence, variant="D", emit_logs=False)
    assert len(patterns) == 1
    assert patterns[0].anchor_phrase == "fraud_prevention|prevent_fraud|fraud_loss"
    assert patterns[0].complaint_count == 3


def test_missing_founder_signals_are_skipped() -> None:
    evidence = [
        ComplaintEvidence(
            id=uuid4(),
            summary="No founder signals on this complaint record.",
            verbatim_quote="Processor removed and billing stopped immediately.",
            severity=4,
            domain_code="fintech",
            category_code="pricing",
            persona_code="founder",
        )
        for _ in range(3)
    ]
    assert detect_founder_signal_patterns(evidence, emit_logs=False) == []


def test_resolve_generation_patterns_uses_founder_signal_when_venture_inapplicable() -> None:
    evidence = [
        _evidence(
            business_function_code="fraud_prevention",
            jtbd_code="prevent_fraud",
            consequence_code="fraud_loss",
            verbatim_quote=quote,
        )
        for quote in (
            "Qwerty alpha uniqueone sentence here.",
            "Asdfgh beta uniquetwo sentence there.",
            "Zxcvbn gamma uniquethree sentence else.",
        )
    ]
    patterns = resolve_generation_patterns(evidence, [])
    assert len(patterns) == 1
    assert patterns[0].pattern_source == PATTERN_SOURCE_FOUNDER_SIGNAL


def test_evaluate_founder_signal_variants_runs_all_four() -> None:
    evidence = [
        _evidence(
            business_function_code="subscription_management",
            jtbd_code="manage_subscriptions",
            consequence_code="revenue_interruption",
        )
        for _ in range(3)
    ]
    results = evaluate_founder_signal_variants(evidence)
    assert set(results) == {"A", "B", "C", "D"}
    assert all(len(patterns) == 1 for patterns in results.values())
