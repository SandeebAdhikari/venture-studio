"""Closed-vocabulary founder signal codes for complaint classification."""

from __future__ import annotations

from typing import Literal

BUSINESS_FUNCTION_CODES: frozenset[str] = frozenset(
    {
        # Fintech / Stripe (V1)
        "payment_processor",
        "fraud_prevention",
        "billing_operations",
        "subscription_management",
        "checkout_optimization",
        "invoice_collection",
        # Engineering (V1 legacy)
        "ci_cd",
        "deployment",
        "observability",
        # AI Infrastructure (V2)
        "agent_tooling",
        "model_operations",
        "inference_governance",
        "llm_evaluation",
        "gpu_compute",
        # Security (V2)
        "vulnerability_management",
        "incident_response",
        "application_security",
        "identity_access",
        # Engineering Platforms (V2)
        "developer_experience",
        "api_platform",
        "internal_platform",
        # Cloud Operations (V2)
        "infrastructure_provisioning",
        "capacity_management",
    }
)

JTBD_CODES: frozenset[str] = frozenset(
    {
        # Fintech / Stripe (V1)
        "accept_payments",
        "prevent_fraud",
        "automate_billing",
        "manage_subscriptions",
        "collect_invoices",
        # Engineering (V1 legacy)
        "deploy_software",
        "monitor_systems",
        # AI Infrastructure (V2)
        "configure_agent_tools",
        "operate_llm_systems",
        "govern_inference_spend",
        "evaluate_model_quality",
        "provision_compute",
        # Security (V2)
        "remediate_vulnerabilities",
        "respond_to_incidents",
        "secure_applications",
        "manage_identity_access",
        # Engineering Platforms (V2)
        "improve_developer_workflow",
        "publish_consume_apis",
        "operate_internal_platforms",
        # Cloud Operations (V2)
        "provision_infrastructure",
        "manage_capacity_quotas",
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
        # V2
        "trust_erosion",
        "innovation_blocked",
    }
)

FounderGroupingVariant = Literal["A", "B", "C", "D", "E"]

DEFAULT_FOUNDER_SIGNAL_VARIANT: FounderGroupingVariant = "B"

# Generic catch-alls must never form clusters (anti-junk).
BLOCKED_FOUNDER_SIGNAL_CODES: frozenset[str] = frozenset()


def founder_signals_prompt_block() -> str:
    return (
        "Founder signal namespace (separate from problem_category — never mix these fields):\n"
        "Fintech: "
        f"{', '.join(sorted({'payment_processor', 'fraud_prevention', 'billing_operations', 'subscription_management', 'checkout_optimization', 'invoice_collection'}))}\n"
        "Engineering (legacy): ci_cd, deployment, observability\n"
        "AI Infrastructure: "
        f"{', '.join(sorted({'agent_tooling', 'model_operations', 'inference_governance', 'llm_evaluation', 'gpu_compute'}))}\n"
        "Security: "
        f"{', '.join(sorted({'vulnerability_management', 'incident_response', 'application_security', 'identity_access'}))}\n"
        "Engineering Platforms: "
        f"{', '.join(sorted({'developer_experience', 'api_platform', 'internal_platform'}))}\n"
        "Cloud Operations: "
        f"{', '.join(sorted({'infrastructure_provisioning', 'capacity_management'}))}\n"
        f"business_function_code must be one of: {', '.join(sorted(BUSINESS_FUNCTION_CODES))}\n"
        f"jtbd_code must be one of: {', '.join(sorted(JTBD_CODES))}\n"
        f"consequence_code must be one of: {', '.join(sorted(CONSEQUENCE_CODES))}\n"
        "billing_operations belongs here as business_function_code only — not problem_category.\n"
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


def format_venture_cluster_key(
    *,
    business_function_code: str,
    jtbd_code: str,
    consequence_code: str,
    mechanism_fingerprint: str,
) -> str:
    return "|".join(
        [
            business_function_code,
            jtbd_code,
            consequence_code,
            mechanism_fingerprint,
        ]
    )
