"""Deterministic mechanism fingerprints for venture-aware pattern formation."""

from __future__ import annotations

import html
import re
from typing import Final

from app.agents.opportunity.schemas import ComplaintEvidence

MECHANISM_FINGERPRINTS: Final[frozenset[str]] = frozenset(
    {
        "processor_account_deplatforming",
        "radar_false_positive_blocking",
        "geo_payment_availability",
        "low_upfront_processor_onboarding",
        "pci_vault_recurring",
        "chargeback_defense",
        "marketplace_fraud_screening",
        "checkout_friction_fraud_tradeoff",
        "usage_metering_per_subscription",
        "gateway_orchestration",
        "api_monetization",
        "processor_fee_optimization",
        "platform_billing_lock_in",
        "hosted_checkout_friction",
        "invoice_workflow_scaling",
        "payment_compliance_friction",
    }
)

SINGLETON_MIN_SEVERITY = 3
MIN_QUOTE_SPECIFICITY_CHARS = 40
MIN_QUOTE_SPECIFICITY_WORDS = 6

_THIN_QUOTE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"^any suggestions\s*\??$", re.IGNORECASE),
    re.compile(r"^help\s*\??$", re.IGNORECASE),
    re.compile(r"^thoughts\s*\??$", re.IGNORECASE),
)

# First matching rule wins — list more specific venture wedges before broad phrases.
_MECHANISM_RULES: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    (
        "processor_account_deplatforming",
        (
            "kicked off stripe",
            "got kicked off stripe",
            "removed from stripe",
            "suspended by stripe",
            "account suspended",
        ),
    ),
    (
        "radar_false_positive_blocking",
        (
            "stripe-radar",
            "stripe radar",
            "radar is hindering",
            "blocked\" payments because of \"high risk",
            "blocked payments because of",
        ),
    ),
    (
        "platform_billing_lock_in",
        (
            "google play billing",
            "must use google play billing",
            "pay 30% to google",
            "pay 30% to google?",
        ),
    ),
    (
        "processor_fee_optimization",
        (
            "50% of the transaction",
            "50% fees",
            "small transactions",
            "fees are relatively high",
            "largest software line item",
        ),
    ),
    (
        "hosted_checkout_friction",
        (
            "payment page is hosted",
            "billing address, zip code and phone",
            "force our customers to enter their billing address",
        ),
    ),
    (
        "invoice_workflow_scaling",
        (
            "20 invoice",
            "invoices per month",
            "xero",
            "volume limit",
        ),
    ),
    (
        "payment_compliance_friction",
        (
            "psd2",
            "strong customer authentication",
            "consumption tax compliance",
            "complying with consumption tax",
        ),
    ),
    (
        "geo_payment_availability",
        (
            "isn't available where i live",
            "isnt available where i live",
            "south africa",
            "isn't available where",
        ),
    ),
    (
        "low_upfront_processor_onboarding",
        (
            "up front costs",
            "upfront costs",
        ),
    ),
    (
        "pci_vault_recurring",
        (
            "credit card vault",
            "pci compliance",
        ),
    ),
    (
        "chargeback_defense",
        (
            "chargeback",
            "fscked sideways",
        ),
    ),
    (
        "marketplace_fraud_screening",
        (
            "preventing credit card fraud",
            "prevent credit card fraud",
            "online selling",
        ),
    ),
    (
        "checkout_friction_fraud_tradeoff",
        (
            "fewer details collected",
            "greater the chance",
            "being fraudulent",
        ),
    ),
    (
        "usage_metering_per_subscription",
        (
            "track usage",
            "per subscription",
            "gb of data",
        ),
    ),
    (
        "gateway_orchestration",
        (
            "supports all of these gateways",
            "subscription management product which supports",
        ),
    ),
    (
        "api_monetization",
        (
            "manage api keys",
            "api keys, users and billing",
            "users and billing",
        ),
    ),
)


def _normalize_evidence_text(*parts: str) -> str:
    combined = " ".join(part for part in parts if part and part.strip())
    decoded = html.unescape(combined)
    lowered = decoded.lower()
    lowered = lowered.replace("&#x27;", "'").replace("&quot;", '"')
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def extract_mechanism_fingerprint(
    *,
    verbatim_quote: str,
    summary: str = "",
) -> str | None:
    """Return the first matching mechanism fingerprint for complaint text."""
    text = _normalize_evidence_text(verbatim_quote, summary)
    if not text:
        return None

    for fingerprint, phrases in _MECHANISM_RULES:
        if any(phrase in text for phrase in phrases):
            return fingerprint
    return None


def passes_quote_specificity(*, verbatim_quote: str, summary: str = "") -> bool:
    """Deterministic quote-specificity gate for founder-grade singleton exceptions."""
    text = html.unescape(verbatim_quote or "").strip()
    if not text:
        return False

    lowered = re.sub(r"\s+", " ", text.lower()).strip()
    for pattern in _THIN_QUOTE_PATTERNS:
        if pattern.match(lowered):
            return False

    words = re.findall(r"[a-z0-9']+", lowered)
    if len(text) >= MIN_QUOTE_SPECIFICITY_CHARS and len(words) >= MIN_QUOTE_SPECIFICITY_WORDS:
        return True

    normalized = _normalize_evidence_text(verbatim_quote, summary)
    if len(normalized) >= MIN_QUOTE_SPECIFICITY_CHARS and len(words) >= MIN_QUOTE_SPECIFICITY_WORDS:
        return True

    return False


def _has_founder_signals(member: ComplaintEvidence) -> bool:
    return bool(
        member.business_function_code
        and member.jtbd_code
        and member.consequence_code
    )


def evaluate_singleton_exception(member: ComplaintEvidence) -> str | None:
    """Return a human-readable reason when a complaint qualifies for singleton formation."""
    if member.severity < SINGLETON_MIN_SEVERITY:
        return None
    if not _has_founder_signals(member):
        return None
    if member.mechanism_fingerprint is None:
        return None
    if member.mechanism_fingerprint not in MECHANISM_FINGERPRINTS:
        return None
    if not passes_quote_specificity(
        verbatim_quote=member.verbatim_quote,
        summary=member.summary,
    ):
        return None
    return (
        f"severity>={SINGLETON_MIN_SEVERITY}; "
        f"mechanism={member.mechanism_fingerprint}; "
        "quote_specificity=high"
    )


def enrich_complaint_evidence(evidence: ComplaintEvidence) -> ComplaintEvidence:
    """Attach a mechanism fingerprint when missing."""
    if evidence.mechanism_fingerprint is not None:
        return evidence

    fingerprint = extract_mechanism_fingerprint(
        verbatim_quote=evidence.verbatim_quote,
        summary=evidence.summary,
    )
    if fingerprint is None:
        return evidence

    return evidence.model_copy(update={"mechanism_fingerprint": fingerprint})
