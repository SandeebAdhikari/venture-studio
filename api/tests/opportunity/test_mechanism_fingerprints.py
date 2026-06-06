"""Tests for deterministic mechanism fingerprint extraction."""

from uuid import uuid4

from app.agents.opportunity.mechanism_fingerprints import (
    SINGLETON_MIN_SEVERITY,
    enrich_complaint_evidence,
    evaluate_singleton_exception,
    extract_mechanism_fingerprint,
    passes_quote_specificity,
)
from app.agents.opportunity.schemas import ComplaintEvidence


def _evidence(
    *,
    quote: str,
    summary: str = "",
    severity: int = 4,
    fingerprint: str | None = None,
    business_function_code: str = "payment_processor",
    jtbd_code: str = "accept_payments",
    consequence_code: str = "revenue_interruption",
) -> ComplaintEvidence:
    return ComplaintEvidence(
        id=uuid4(),
        summary=summary or "Stripe billing complaint summary for testing.",
        verbatim_quote=quote,
        severity=severity,
        domain_code="fintech",
        category_code="pricing",
        persona_code="founder",
        business_function_code=business_function_code,
        jtbd_code=jtbd_code,
        consequence_code=consequence_code,
        mechanism_fingerprint=fingerprint,
    )


def test_extracts_processor_account_deplatforming_fingerprint() -> None:
    quote = (
        "I just got kicked off Stripe; classified as high risk. "
        "Where else can I go for SaaS billing?"
    )
    assert extract_mechanism_fingerprint(verbatim_quote=quote) == "processor_account_deplatforming"


def test_extracts_radar_false_positive_blocking_fingerprint() -> None:
    quote = (
        'the Stripe-Radar is hindering the subscriptions. Yesterday, we experienced '
        '2-digit "Blocked" payments because of "High Risk".'
    )
    assert extract_mechanism_fingerprint(verbatim_quote=quote) == "radar_false_positive_blocking"


def test_deplatforming_and_radar_are_distinct_fingerprints() -> None:
    deplatform = "I just got kicked off Stripe; classified as high risk."
    radar = 'Stripe-Radar blocked payments because of "High Risk".'
    assert extract_mechanism_fingerprint(verbatim_quote=deplatform) == (
        "processor_account_deplatforming"
    )
    assert extract_mechanism_fingerprint(verbatim_quote=radar) == "radar_false_positive_blocking"


def test_extracts_usage_metering_fingerprint() -> None:
    quote = "Stripe does not allow me to track usage ( such as how much GB of data is used ) per subscription."
    assert extract_mechanism_fingerprint(verbatim_quote=quote) == "usage_metering_per_subscription"


def test_extracts_platform_billing_lock_in_fingerprint() -> None:
    quote = (
        "How is this legal that if I want to publish an Android app on Play Market "
        "and charge for subscriptions, I must use Google Play Billing and pay 30% to Google?"
    )
    assert extract_mechanism_fingerprint(verbatim_quote=quote) == "platform_billing_lock_in"


def test_extracts_processor_fee_optimization_fingerprint() -> None:
    quote = "PayPal and Stripe both charge around 50% of the transaction for small payments."
    assert extract_mechanism_fingerprint(verbatim_quote=quote) == "processor_fee_optimization"


def test_extracts_hosted_checkout_friction_fingerprint() -> None:
    quote = (
        "since the payment page is hosted on their end, they force our customers to enter "
        "their billing address, zip code and phone number"
    )
    assert extract_mechanism_fingerprint(verbatim_quote=quote) == "hosted_checkout_friction"


def test_extracts_payment_compliance_friction_fingerprint() -> None:
    quote = "I have been greatly frustrated by the apparent lack of standard advice for PSD2 compliance."
    assert extract_mechanism_fingerprint(verbatim_quote=quote) == "payment_compliance_friction"


def test_thin_quote_fails_specificity_gate() -> None:
    assert passes_quote_specificity(verbatim_quote="Any suggestions ?") is False


def test_singleton_exception_requires_specific_quote() -> None:
    member = enrich_complaint_evidence(
        _evidence(
            quote="Any suggestions ?",
            summary="Preventing credit card fraud on their online selling platform.",
            severity=4,
        )
    )
    member = member.model_copy(update={"mechanism_fingerprint": "marketplace_fraud_screening"})
    assert evaluate_singleton_exception(member) is None


def test_singleton_exception_passes_at_severity_three_with_mechanism() -> None:
    quote = (
        "Unfortunately Stripe and Braintree isn't available where I live (South Africa), "
        "making accepting payments (subscriptions) in an international market a bit more difficult."
    )
    member = enrich_complaint_evidence(_evidence(quote=quote, severity=3))
    reason = evaluate_singleton_exception(member)
    assert reason is not None
    assert f"severity>={SINGLETON_MIN_SEVERITY}" in reason
    assert "geo_payment_availability" in reason


def test_singleton_exception_passes_for_processor_deplatforming() -> None:
    member = enrich_complaint_evidence(
        _evidence(
            quote=(
                "I just got kicked off Stripe; classified as high risk. "
                "Where else can I go for SaaS billing?"
            )
        )
    )
    reason = evaluate_singleton_exception(member)
    assert reason is not None
    assert "processor_account_deplatforming" in reason
