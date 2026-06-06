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
        "vulnerability_disclosure_workflow",
        "endpoint_security_negligence",
        "session_fixation_exposure",
        "incident_response_coordination",
        "credential_exposure_detection",
        "agentic_code_trust_gap",
        "mcp_discovery_overhead",
        "cicd_yaml_complexity",
        "pipeline_template_rigidity",
        "local_dev_performance",
        "platform_api_dx_friction",
        "openapi_spec_friction",
        "coding_agent_api_spec_gap",
        "mcp_context_budget_overflow",
        "llm_guardrail_engineering_tax",
        "ai_eval_pipeline_gap",
        "inference_cost_governance",
        "gpu_compute_access_unreliability",
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
        "session_fixation_exposure",
        (
            "session fixation vulnerability",
            "session id is the user",
            "session id is the user's email",
        ),
    ),
    (
        "vulnerability_disclosure_workflow",
        (
            "reporting a security vulnerability",
            "risked termination and i should tell someone first",
            "reprimanded for reporting a security vulnerability",
        ),
    ),
    (
        "endpoint_security_negligence",
        (
            "found a security vulnerability in a web page",
            "easily-guessable url",
            "gives away a file containing a password",
            "reported that vulnerability immediately",
            "would look into it and reply. he did not",
            "look into it and reply. he did not",
        ),
    ),
    (
        "incident_response_coordination",
        (
            "ransomware attack",
            "criminally negligent in their data security",
        ),
    ),
    (
        "credential_exposure_detection",
        (
            "email accounts has been broken into",
            "suspect malware on my laptop",
        ),
    ),
    (
        "agentic_code_trust_gap",
        (
            "0 trust in the quality of the generated code",
            "absolutely 0 trust in the quality of the generated code",
        ),
    ),
    (
        "mcp_discovery_overhead",
        (
            "discovering and configuring mcp servers",
            "time-consuming and not \"agentic\"",
            "time-consuming and not agentic",
        ),
    ),
    (
        "coding_agent_api_spec_gap",
        (
            "coding agents struggle to get the current openai api spec",
            "struggle to get the current openai api spec",
            "difficulty in accessing the official openai api specification",
        ),
    ),
    (
        "mcp_context_budget_overflow",
        (
            "cross the input context length limit",
            "blows up the context window",
            "mcp sources can give a huge output",
        ),
    ),
    (
        "llm_guardrail_engineering_tax",
        (
            "80% of my engineering effort building guardrails",
            "building guardrails to prevent hallucinations",
        ),
    ),
    (
        "ai_eval_pipeline_gap",
        (
            "build a proper evaluation pipeline for months",
            "every tool we've tested has significant limitations",
        ),
    ),
    (
        "inference_cost_governance",
        (
            "claude bill has become astronomical",
            "3x our saas's cloud spend",
            "rapidly cutting ai tool spend",
        ),
    ),
    (
        "gpu_compute_access_unreliability",
        (
            "performance are all over the place compared to what's listed",
            "renting gpus a handful of times and hosts, bandwidth",
            "paid google colab options don't work",
        ),
    ),
    (
        "cicd_yaml_complexity",
        (
            "reliance on yaml configurations",
            "complexity of existing ci/cd tools",
        ),
    ),
    (
        "pipeline_template_rigidity",
        (
            "lack of freedom for the developers",
            "templated build pipelines for ci/cd",
            "pushback because of it",
        ),
    ),
    (
        "local_dev_performance",
        (
            "loading a page in the rails app from the host machine is just too damn slow",
            "5 to 10+ seconds to refresh the page",
        ),
    ),
    (
        "platform_api_dx_friction",
        (
            "fed up with their terrible developer experience",
            "built integrations for hubspot",
        ),
    ),
    (
        "openapi_spec_friction",
        (
            "writing the open api spec in yaml is tedious",
            "open api documentation constantly while writing the spec",
        ),
    ),
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
