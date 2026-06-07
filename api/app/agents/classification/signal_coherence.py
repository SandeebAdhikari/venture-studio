"""Signal–mechanism coherence checks for founder signal overlays and topics."""

from __future__ import annotations

from typing import Final

from app.agents.classification.founder_signals import (
    BUSINESS_FUNCTION_CODES,
    JTBD_CODES,
)

FINTECH_MECHANISMS: Final[frozenset[str]] = frozenset(
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

FINTECH_BUSINESS_FUNCTIONS: frozenset[str] = frozenset(
    {
        "payment_processor",
        "fraud_prevention",
        "billing_operations",
        "subscription_management",
        "checkout_optimization",
        "invoice_collection",
    }
)

FINTECH_JTBD_CODES: frozenset[str] = frozenset(
    {
        "accept_payments",
        "prevent_fraud",
        "automate_billing",
        "manage_subscriptions",
        "collect_invoices",
    }
)

BLOCKED_CROSS_DOMAIN_BUSINESS_FUNCTIONS: frozenset[str] = FINTECH_BUSINESS_FUNCTIONS

BLOCKED_CROSS_DOMAIN_JTBD_CODES: frozenset[str] = FINTECH_JTBD_CODES

# Expected business function per non-fintech mechanism fingerprint.
MECHANISM_EXPECTED_BUSINESS_FUNCTION: dict[str, frozenset[str]] = {
    "mcp_discovery_overhead": frozenset({"agent_tooling"}),
    "mcp_context_budget_overflow": frozenset({"agent_tooling"}),
    "llm_guardrail_engineering_tax": frozenset({"model_operations"}),
    "ai_eval_pipeline_gap": frozenset({"llm_evaluation"}),
    "inference_cost_governance": frozenset({"inference_governance"}),
    "gpu_compute_access_unreliability": frozenset({"gpu_compute", "capacity_management"}),
    "coding_agent_api_spec_gap": frozenset({"api_platform"}),
    "vulnerability_disclosure_workflow": frozenset({"vulnerability_management"}),
    "incident_response_coordination": frozenset({"incident_response"}),
    "session_fixation_exposure": frozenset({"application_security"}),
    "endpoint_security_negligence": frozenset({"vulnerability_management"}),
    "cicd_yaml_complexity": frozenset({"ci_cd"}),
    "pipeline_template_rigidity": frozenset({"ci_cd"}),
    "local_dev_performance": frozenset({"deployment"}),
    "openapi_spec_friction": frozenset({"api_platform"}),
    "platform_api_dx_friction": frozenset({"internal_platform"}),
    "agentic_code_trust_gap": frozenset({"developer_experience"}),
}


def has_cross_domain_signal_leakage(
    *,
    business_function_code: str | None,
    jtbd_code: str | None,
) -> bool:
    if business_function_code in BLOCKED_CROSS_DOMAIN_BUSINESS_FUNCTIONS:
        return True
    return jtbd_code in BLOCKED_CROSS_DOMAIN_JTBD_CODES


def signal_mechanism_coherent(
    business_function_code: str | None,
    mechanism_fingerprint: str | None,
) -> bool:
    """Return True when the business function matches the mechanism family."""
    if not business_function_code or not mechanism_fingerprint:
        return True

    expected = MECHANISM_EXPECTED_BUSINESS_FUNCTION.get(mechanism_fingerprint)
    if expected is None:
        return True

    return business_function_code in expected


def incoherence_reason(
    *,
    business_function_code: str | None,
    jtbd_code: str | None,
    mechanism_fingerprint: str | None,
) -> str | None:
    if mechanism_fingerprint is None:
        return None

    if has_cross_domain_signal_leakage(
        business_function_code=business_function_code,
        jtbd_code=jtbd_code,
    ):
        return "cross_domain_fintech_signal"

    if business_function_code and business_function_code not in BUSINESS_FUNCTION_CODES:
        return "unknown_business_function"

    if jtbd_code and jtbd_code not in JTBD_CODES:
        return "unknown_jtbd"

    if not signal_mechanism_coherent(business_function_code, mechanism_fingerprint):
        return "mechanism_bf_mismatch"

    return None
