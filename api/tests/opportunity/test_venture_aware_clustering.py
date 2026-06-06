"""Tests for venture-aware clustering and formation policy."""

from uuid import UUID, uuid4

from app.agents.opportunity.mechanism_fingerprints import enrich_complaint_evidence
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.taxonomy_fallback import resolve_generation_patterns
from app.agents.opportunity.venture_aware_clustering import detect_venture_aware_patterns

STRIPE_R1_R3: list[tuple[str, str, str, str, str, int]] = [
    (
        "191e82f8-18a1-4d17-9bb1-2adff6aabe87",
        "payment_processor",
        "accept_payments",
        "revenue_interruption",
        "I just got kicked off Stripe; classified as high risk. Where else can I go for SaaS billing?",
        4,
    ),
    (
        "c80adb68-44b5-49e6-b47f-be8982d9a054",
        "payment_processor",
        "accept_payments",
        "margin_erosion",
        "the up front costs are relatively high.",
        3,
    ),
    (
        "a4d30dbe-dbee-4762-b576-c4c520ed1d17",
        "payment_processor",
        "accept_payments",
        "revenue_interruption",
        "Unfortunately Stripe and Braintree isn't available where I live (South Africa), making accepting payments (subscriptions) in an international market a bit more difficult.",
        3,
    ),
    (
        "7e1446aa-d438-4460-bcad-d5f9ccaee94f",
        "payment_processor",
        "accept_payments",
        "operational_risk",
        "I'm trying to find a credit card processor that supports recurring billing or has a 'credit card vault' where they store the cards so I don't need to worry about PCI compliance.",
        3,
    ),
    (
        "948e6176-2c11-4006-b010-98bcc312c273",
        "fraud_prevention",
        "prevent_fraud",
        "margin_erosion",
        "Why are we getting fscked sideways by Stripe, BoA & the customer ?",
        4,
    ),
    (
        "57577e0b-2b86-4176-8e59-042361a3b77d",
        "fraud_prevention",
        "prevent_fraud",
        "fraud_loss",
        "Any suggestions ?",
        4,
    ),
    (
        "df278195-acc0-45d8-9b10-a94bf92d23f4",
        "fraud_prevention",
        "prevent_fraud",
        "fraud_loss",
        "I am concerned that the fewer details collected in the payment form, the greater the chance of a given transaction being fraudulent.",
        3,
    ),
    (
        "4281360c-288c-43b9-a70e-48ba450f271d",
        "subscription_management",
        "manage_subscriptions",
        "revenue_interruption",
        "Stripe does not allow me to track usage ( such as how much GB of data is used ) per subscription.",
        4,
    ),
    (
        "988dadac-1460-4606-bcc3-505b7b7c3981",
        "subscription_management",
        "manage_subscriptions",
        "revenue_interruption",
        "Why there isn't any subscription management product which supports all of these gateways?",
        3,
    ),
    (
        "4e3de199-4f95-4f7a-bcb6-c0ab1d1e83c4",
        "billing_operations",
        "automate_billing",
        "engineering_friction",
        "I want a simple solution to manage API keys, users and billing.",
        3,
    ),
]


def _stripe_evidence() -> list[ComplaintEvidence]:
    items: list[ComplaintEvidence] = []
    for complaint_id, bf, jtbd, consequence, quote, severity in STRIPE_R1_R3:
        items.append(
            enrich_complaint_evidence(
                ComplaintEvidence(
                    id=UUID(complaint_id),
                    summary=f"Summary for {complaint_id[:8]}",
                    verbatim_quote=quote,
                    severity=severity,
                    domain_code="fintech",
                    category_code="pricing",
                    persona_code="founder",
                    product_mentions=["Stripe"],
                    business_function_code=bf,
                    jtbd_code=jtbd,
                    consequence_code=consequence,
                )
            )
        )
    return items


def test_stripe_r1_r3_forms_singleton_exceptions_not_zero_patterns() -> None:
    patterns = detect_venture_aware_patterns(_stripe_evidence(), emit_logs=False)
    assert len(patterns) >= 6

    singletons = [pattern for pattern in patterns if pattern.singleton_exception_reason]
    assert len(singletons) >= 6

    mechanisms = {pattern.mechanism_fingerprint for pattern in singletons}
    assert "processor_account_deplatforming" in mechanisms
    assert "chargeback_defense" in mechanisms
    assert "usage_metering_per_subscription" in mechanisms
    assert "geo_payment_availability" in mechanisms
    assert "pci_vault_recurring" in mechanisms
    assert "api_monetization" in mechanisms


def test_legacy_bf_jtbd_cluster_not_used_when_venture_patterns_exist() -> None:
    patterns = resolve_generation_patterns(_stripe_evidence(), [])
    assert len(patterns) >= 6
    assert all(pattern.founder_grouping_variant == "E" for pattern in patterns)


def test_impure_bf_jtbd_cluster_avoided_for_r1() -> None:
    patterns = resolve_generation_patterns(_stripe_evidence(), [])
    assert not any(pattern.complaint_count == 4 for pattern in patterns)


def test_cluster_size_two_emits_independent_singleton_patterns() -> None:
    quote_one = "Why are we getting fscked sideways by Stripe, BoA & the customer ?"
    quote_two = (
        "Every chargeback on our SaaS subscription hits us with Stripe fees and manual dispute work."
    )
    shared_key_evidence = [
        enrich_complaint_evidence(
            ComplaintEvidence(
                id=uuid4(),
                summary="Chargeback fee pain",
                verbatim_quote=quote_one,
                severity=4,
                domain_code="fintech",
                category_code="pricing",
                persona_code="founder",
                business_function_code="billing_operations",
                jtbd_code="collect_invoices",
                consequence_code="operational_overhead",
            )
        ),
        enrich_complaint_evidence(
            ComplaintEvidence(
                id=uuid4(),
                summary="Chargeback dispute overhead",
                verbatim_quote=quote_two,
                severity=4,
                domain_code="fintech",
                category_code="pricing",
                persona_code="founder",
                business_function_code="billing_operations",
                jtbd_code="collect_invoices",
                consequence_code="operational_overhead",
            )
        ),
    ]
    patterns = detect_venture_aware_patterns(shared_key_evidence, emit_logs=False)
    assert len(patterns) == 2
    assert all(pattern.complaint_count == 1 for pattern in patterns)
    assert all(pattern.mechanism_fingerprint == "chargeback_defense" for pattern in patterns)
    assert len({pattern.complaint_ids[0] for pattern in patterns}) == 2


def test_deplatforming_and_radar_use_distinct_cluster_keys() -> None:
    evidence = [
        enrich_complaint_evidence(
            ComplaintEvidence(
                id=uuid4(),
                summary="Deplatforming complaint",
                verbatim_quote="I just got kicked off Stripe; classified as high risk.",
                severity=4,
                domain_code="fintech",
                category_code="security",
                persona_code="founder",
                business_function_code="payment_processor",
                jtbd_code="accept_payments",
                consequence_code="revenue_interruption",
            )
        ),
        enrich_complaint_evidence(
            ComplaintEvidence(
                id=uuid4(),
                summary="Radar blocking complaint",
                verbatim_quote=(
                    'Stripe-Radar blocked payments because of "High Risk" on subscriptions.'
                ),
                severity=4,
                domain_code="fintech",
                category_code="performance",
                persona_code="founder",
                business_function_code="payment_processor",
                jtbd_code="accept_payments",
                consequence_code="revenue_interruption",
            )
        ),
    ]
    patterns = detect_venture_aware_patterns(evidence, emit_logs=False)
    assert len(patterns) == 2
    mechanisms = {pattern.mechanism_fingerprint for pattern in patterns}
    assert mechanisms == {
        "processor_account_deplatforming",
        "radar_false_positive_blocking",
    }
