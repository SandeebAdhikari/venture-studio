"""Tests for founder-thesis opportunity generation prompt construction."""

from uuid import uuid4

from app.agents.opportunity.llm_client import (
    BANNED_TITLE_PATTERNS,
    FOUNDER_CONSEQUENCE_CODES,
    FOUNDER_THESIS_SYSTEM_PROMPT,
    OpenAIOpportunityClient,
    build_opportunity_synthesis_messages,
    build_opportunity_user_prompt,
    format_opportunity_evidence,
)
from app.agents.opportunity.schemas import ComplaintEvidence, ComplaintPattern


def _evidence(
    *,
    summary: str,
    quote: str,
    severity: int = 4,
    persona_code: str = "founder",
    product_mentions: list[str] | None = None,
    business_function_code: str | None = None,
    jtbd_code: str | None = None,
    consequence_code: str | None = None,
) -> ComplaintEvidence:
    return ComplaintEvidence(
        id=uuid4(),
        summary=summary,
        verbatim_quote=quote,
        severity=severity,
        domain_code="saas_b2b",
        category_code="pricing",
        persona_code=persona_code,
        product_mentions=product_mentions or ["Stripe"],
        business_function_code=business_function_code,
        jtbd_code=jtbd_code,
        consequence_code=consequence_code,
    )


def _pattern(
    *,
    topic: str,
    anchor: str,
    evidence: list[ComplaintEvidence],
    business_function_code: str | None = None,
    jtbd_code: str | None = None,
    consequence_code: str | None = None,
) -> ComplaintPattern:
    return ComplaintPattern(
        topic=topic,
        anchor_phrase=anchor,
        complaint_ids=[item.id for item in evidence],
        domain_code="fintech",
        category_code="pricing",
        dominant_persona_code="founder",
        complaint_count=len(evidence),
        avg_severity=sum(item.severity for item in evidence) / len(evidence),
        pattern_source="founder_signal_clustering",
        founder_grouping_variant="B",
        business_function_code=business_function_code,
        jtbd_code=jtbd_code,
        consequence_code=consequence_code,
    )


def _r1_fixtures() -> tuple[ComplaintPattern, list[ComplaintEvidence]]:
    evidence = [
        _evidence(
            summary="Removed from Stripe; seeks SaaS billing alternatives.",
            quote="I just got kicked off Stripe; classified as high risk.",
            business_function_code="payment_processor",
            jtbd_code="accept_payments",
            consequence_code="revenue_interruption",
        ),
        _evidence(
            summary="EU Stripe alternatives; high upfront costs.",
            quote="the up front costs are relatively high.",
            severity=3,
            business_function_code="payment_processor",
            jtbd_code="accept_payments",
            consequence_code="margin_erosion",
        ),
    ]
    pattern = _pattern(
        topic="Payment Processor — Accept Payments",
        anchor="payment_processor|accept_payments",
        evidence=evidence,
        business_function_code="payment_processor",
        jtbd_code="accept_payments",
        consequence_code=None,
    )
    return pattern, evidence


def _r2_fixtures() -> tuple[ComplaintPattern, list[ComplaintEvidence]]:
    evidence = [
        _evidence(
            summary="Unexpected chargeback fees despite low chargeback rate.",
            quote="Why are we getting fscked sideways by Stripe, BoA & the customer ?",
            business_function_code="fraud_prevention",
            jtbd_code="prevent_fraud",
            consequence_code="margin_erosion",
        ),
        _evidence(
            summary="Preventing credit card fraud on online selling platform.",
            quote="Any suggestions ?",
            business_function_code="fraud_prevention",
            jtbd_code="prevent_fraud",
            consequence_code="fraud_loss",
        ),
    ]
    pattern = _pattern(
        topic="Fraud Prevention — Prevent Fraud",
        anchor="fraud_prevention|prevent_fraud",
        evidence=evidence,
        business_function_code="fraud_prevention",
        jtbd_code="prevent_fraud",
        consequence_code=None,
    )
    return pattern, evidence


def _r3_fixtures() -> tuple[ComplaintPattern, list[ComplaintEvidence]]:
    evidence = [
        ComplaintEvidence(
            id=uuid4(),
            summary="Stripe cannot track usage per subscription.",
            verbatim_quote="Stripe does not allow me to track usage per subscription.",
            severity=4,
            domain_code="saas_b2b",
            category_code="missing_feature",
            persona_code="founder",
            product_mentions=["Stripe", "KillBill"],
            business_function_code="subscription_management",
            jtbd_code="manage_subscriptions",
            consequence_code="revenue_interruption",
        ),
        ComplaintEvidence(
            id=uuid4(),
            summary="Simple API keys, users, and billing monetization.",
            verbatim_quote="I want a simple solution to manage API keys, users and billing.",
            severity=3,
            domain_code="devtools",
            category_code="missing_feature",
            persona_code="developer",
            product_mentions=["Stripe"],
            business_function_code="billing_operations",
            jtbd_code="automate_billing",
            consequence_code="engineering_friction",
        ),
    ]
    pattern = ComplaintPattern(
        topic="Billing Model Infrastructure",
        anchor_phrase="billing_model_infrastructure",
        complaint_ids=[item.id for item in evidence],
        domain_code="saas_b2b",
        category_code="missing_feature",
        dominant_persona_code="developer",
        complaint_count=len(evidence),
        avg_severity=3.5,
        pattern_source="founder_signal_clustering",
        founder_grouping_variant="B",
        business_function_code="billing_operations",
        jtbd_code="automate_billing",
        consequence_code=None,
    )
    return pattern, evidence


def test_system_prompt_is_founder_thesis_extraction() -> None:
    assert "You extract founder venture theses from complaint evidence" in FOUNDER_THESIS_SYSTEM_PROMPT
    assert "Monday morning build test" in FOUNDER_THESIS_SYSTEM_PROMPT
    assert "Solutions for" in FOUNDER_THESIS_SYSTEM_PROMPT


def test_user_prompt_contains_four_steps() -> None:
    pattern, evidence = _r1_fixtures()
    prompt = build_opportunity_user_prompt(pattern=pattern, evidence=evidence, attempt=1)

    assert "=== STEP 1: COMPLAINT EVIDENCE" in prompt
    assert "=== STEP 2: WEDGE SELECTION" in prompt
    assert "=== STEP 3: CLUSTER CONTEXT" in prompt
    assert "=== STEP 4: OUTPUT ===" in prompt


def test_wedge_selection_section_exists() -> None:
    pattern, evidence = _r1_fixtures()
    prompt = build_opportunity_user_prompt(pattern=pattern, evidence=evidence, attempt=1)

    assert "dominant_complaint:" in prompt
    assert "dominant_wedge:" in prompt
    assert "excluded_pains:" in prompt
    assert "economic_stake:" in prompt


def test_dominant_complaint_and_excluded_pain_instructions_exist() -> None:
    pattern, evidence = _r1_fixtures()
    prompt = build_opportunity_user_prompt(pattern=pattern, evidence=evidence, attempt=1)

    assert "highest severity first" in prompt
    assert "most specific quote" in prompt
    assert "clearest economic consequence" in prompt
    assert "Do NOT merge excluded pains into the title or problem_statement" in prompt


def test_anti_category_rules_exist() -> None:
    pattern, evidence = _r1_fixtures()
    prompt = build_opportunity_user_prompt(pattern=pattern, evidence=evidence, attempt=1)

    for banned in BANNED_TITLE_PATTERNS:
        assert banned in prompt

    assert "invalid because they hide the mechanism" in prompt
    assert "fail the build test" in FOUNDER_THESIS_SYSTEM_PROMPT


def test_founder_consequence_instructions_exist() -> None:
    pattern, evidence = _r1_fixtures()
    prompt = build_opportunity_user_prompt(pattern=pattern, evidence=evidence, attempt=1)

    for code in FOUNDER_CONSEQUENCE_CODES:
        assert code in prompt
        assert code in FOUNDER_THESIS_SYSTEM_PROMPT


def test_evidence_ordering_is_quote_first() -> None:
    item = _evidence(
        summary="Billing pain summary text.",
        quote="Dominant quote text.",
        business_function_code="payment_processor",
        jtbd_code="accept_payments",
        consequence_code="revenue_interruption",
    )
    block = format_opportunity_evidence([item])

    quote_pos = block.index("quote:")
    consequence_pos = block.index("economic_consequence:")
    signals_pos = block.index("founder_signals(")
    summary_pos = block.index("summary:")

    assert quote_pos < consequence_pos < signals_pos < summary_pos


def test_format_evidence_includes_per_complaint_founder_signals() -> None:
    item = _evidence(
        summary="Billing pain",
        quote="Stripe kicked me off.",
        business_function_code="payment_processor",
        jtbd_code="accept_payments",
        consequence_code="revenue_interruption",
    )

    block = OpenAIOpportunityClient._format_evidence([item])

    assert "founder_signals(" in block
    assert "business_function=payment_processor" in block
    assert "jtbd=accept_payments" in block
    assert "economic_consequence: revenue_interruption" in block


def test_format_evidence_uses_unknown_for_missing_founder_signals() -> None:
    item = _evidence(summary="Billing pain", quote="Stripe kicked me off.")

    block = OpenAIOpportunityClient._format_evidence([item])

    assert "economic_consequence: unknown" in block
    assert "business_function=unknown" in block
    assert "jtbd=unknown" in block


def test_cluster_context_includes_pattern_founder_signals() -> None:
    pattern, evidence = _r1_fixtures()
    prompt = build_opportunity_user_prompt(pattern=pattern, evidence=evidence, attempt=1)

    assert "Pattern topic (internal cluster label only)" in prompt
    assert "Pattern founder signals (supporting hints only)" in prompt
    assert "business_function=payment_processor" in prompt
    assert "jtbd=accept_payments" in prompt
    assert "do not copy labels into title" in prompt


def test_synthesis_messages_include_founder_signals_for_r1_r2_r3() -> None:
    cases = [
        ("R1", *_r1_fixtures()),
        ("R2", *_r2_fixtures()),
        ("R3", *_r3_fixtures()),
    ]
    for label, pattern, evidence in cases:
        messages = build_opportunity_synthesis_messages(
            pattern=pattern,
            evidence=evidence,
            attempt=1,
        )
        user_prompt = messages[1]["content"]
        system_prompt = messages[0]["content"]

        assert system_prompt == FOUNDER_THESIS_SYSTEM_PROMPT, label
        assert "=== STEP 1: COMPLAINT EVIDENCE" in user_prompt, label
        assert f"business_function={pattern.business_function_code}" in user_prompt, label
        for item in evidence:
            assert item.verbatim_quote in user_prompt, label
            assert f"consequence={item.consequence_code}" in user_prompt, label


def test_r2_prompt_preserves_margin_erosion_vs_fraud_loss_distinction() -> None:
    pattern, evidence = _r2_fixtures()
    prompt = build_opportunity_user_prompt(pattern=pattern, evidence=evidence, attempt=1)

    assert "economic_consequence: margin_erosion" in prompt
    assert "consequence=fraud_loss" in prompt


def test_retry_block_still_appended() -> None:
    pattern, evidence = _r1_fixtures()

    prompt = build_opportunity_user_prompt(
        pattern=pattern,
        evidence=evidence,
        attempt=2,
        validation_errors=["title is too short"],
    )

    assert "Previous validation errors" in prompt
    assert "title is too short" in prompt
    assert "=== STEP 4: OUTPUT ===" in prompt


def test_r1_r2_r3_prompt_payload_examples() -> None:
    """Document expected prompt sections for manual R1/R2/R3 patterns."""
    for label, fixtures in [
        ("R1", _r1_fixtures),
        ("R2", _r2_fixtures),
        ("R3", _r3_fixtures),
    ]:
        pattern, evidence = fixtures()
        prompt = build_opportunity_user_prompt(pattern=pattern, evidence=evidence, attempt=1)
        assert label in {"R1", "R2", "R3"}
        assert prompt.index("=== STEP 1") < prompt.index("=== STEP 2") < prompt.index("=== STEP 3") < prompt.index("=== STEP 4")
