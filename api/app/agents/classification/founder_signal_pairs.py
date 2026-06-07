"""Allowed business-function / JTBD pairings for founder signal coherence."""

from __future__ import annotations

ALLOWED_BF_JTBD_PAIRS: dict[str, frozenset[str]] = {
    # Fintech / Stripe (V1)
    "payment_processor": frozenset({"accept_payments"}),
    "fraud_prevention": frozenset({"prevent_fraud"}),
    "billing_operations": frozenset({"automate_billing"}),
    "subscription_management": frozenset({"manage_subscriptions"}),
    "checkout_optimization": frozenset({"accept_payments"}),
    "invoice_collection": frozenset({"collect_invoices"}),
    # Engineering (V1 legacy + V2)
    "ci_cd": frozenset({"deploy_software"}),
    "deployment": frozenset({"deploy_software", "monitor_systems"}),
    "observability": frozenset({"monitor_systems", "deploy_software"}),
    "developer_experience": frozenset({"improve_developer_workflow"}),
    "api_platform": frozenset({"publish_consume_apis"}),
    "internal_platform": frozenset({"operate_internal_platforms"}),
    # AI Infrastructure (V2)
    "agent_tooling": frozenset({"configure_agent_tools"}),
    "model_operations": frozenset({"operate_llm_systems"}),
    "inference_governance": frozenset({"govern_inference_spend"}),
    "llm_evaluation": frozenset({"evaluate_model_quality"}),
    "gpu_compute": frozenset({"provision_compute"}),
    # Security (V2)
    "vulnerability_management": frozenset({"remediate_vulnerabilities"}),
    "incident_response": frozenset({"respond_to_incidents"}),
    "application_security": frozenset({"secure_applications"}),
    "identity_access": frozenset({"manage_identity_access"}),
    # Cloud Operations (V2)
    "infrastructure_provisioning": frozenset({"provision_infrastructure"}),
    "capacity_management": frozenset({"manage_capacity_quotas"}),
}


def validate_bf_jtbd_pair(business_function_code: str, jtbd_code: str) -> bool:
    """Return True when the BF/JTBD pair is in the allowed matrix."""
    allowed = ALLOWED_BF_JTBD_PAIRS.get(business_function_code)
    if allowed is None:
        return False
    return jtbd_code in allowed
