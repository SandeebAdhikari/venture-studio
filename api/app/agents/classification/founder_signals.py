"""Closed-vocabulary founder signal codes for complaint classification."""

from __future__ import annotations

from typing import Literal

BUSINESS_FUNCTION_CODES: frozenset[str] = frozenset(
    {
        "payment_processor",
        "fraud_prevention",
        "billing_operations",
        "subscription_management",
        "checkout_optimization",
        "invoice_collection",
        "ci_cd",
        "deployment",
        "observability",
    }
)

JTBD_CODES: frozenset[str] = frozenset(
    {
        "accept_payments",
        "prevent_fraud",
        "automate_billing",
        "manage_subscriptions",
        "deploy_software",
        "monitor_systems",
        "collect_invoices",
    }
)

CONSEQUENCE_CODES: frozenset[str] = frozenset(
    {
        "revenue_interruption",
        "margin_erosion",
        "fraud_loss",
        "operational_overhead",
        "customer_loss",
        "engineering_friction",
        "operational_risk",
    }
)

FounderGroupingVariant = Literal["A", "B", "C", "D"]

DEFAULT_FOUNDER_SIGNAL_VARIANT: FounderGroupingVariant = "B"

# Generic catch-alls must never form clusters (anti-junk).
BLOCKED_FOUNDER_SIGNAL_CODES: frozenset[str] = frozenset()


def founder_signals_prompt_block() -> str:
    return (
        "Founder signal codes (closed vocabulary — pick the best fit, never invent codes):\n"
        f"business_function_code must be one of: {', '.join(sorted(BUSINESS_FUNCTION_CODES))}\n"
        f"jtbd_code must be one of: {', '.join(sorted(JTBD_CODES))}\n"
        f"consequence_code must be one of: {', '.join(sorted(CONSEQUENCE_CODES))}\n"
        "When is_complaint is false, still return valid codes that best describe the text."
    )


def validate_business_function_code(code: str) -> str | None:
    if code in BLOCKED_FOUNDER_SIGNAL_CODES:
        return None
    if code not in BUSINESS_FUNCTION_CODES:
        return None
    return code


def validate_jtbd_code(code: str) -> str | None:
    if code in BLOCKED_FOUNDER_SIGNAL_CODES:
        return None
    if code not in JTBD_CODES:
        return None
    return code


def validate_consequence_code(code: str) -> str | None:
    if code in BLOCKED_FOUNDER_SIGNAL_CODES:
        return None
    if code not in CONSEQUENCE_CODES:
        return None
    return code


def validate_founder_signal_codes(
    *,
    business_function_code: str,
    jtbd_code: str,
    consequence_code: str,
) -> tuple[str, str, str] | None:
    bf = validate_business_function_code(business_function_code)
    jtbd = validate_jtbd_code(jtbd_code)
    consequence = validate_consequence_code(consequence_code)
    if bf is None or jtbd is None or consequence is None:
        return None
    return bf, jtbd, consequence


def format_founder_cluster_key(
    *,
    business_function_code: str,
    jtbd_code: str | None = None,
    consequence_code: str | None = None,
) -> str:
    parts = [business_function_code]
    if jtbd_code is not None:
        parts.append(jtbd_code)
    if consequence_code is not None:
        parts.append(consequence_code)
    return "|".join(parts)
