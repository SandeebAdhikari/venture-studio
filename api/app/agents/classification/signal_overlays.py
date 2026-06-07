"""Deterministic mechanism-to-signal overlays applied at evidence enrichment time."""

from __future__ import annotations

from typing import NamedTuple

from app.agents.classification.signal_coherence import (
    FINTECH_MECHANISMS,
    has_cross_domain_signal_leakage,
    signal_mechanism_coherent,
)
from app.agents.opportunity.schemas import ComplaintEvidence
from app.logging import get_logger

logger = get_logger(__name__)


class SignalOverlay(NamedTuple):
    business_function_code: str
    jtbd_code: str
    consequence_code: str


SIGNAL_OVERLAY_MAP: dict[str, SignalOverlay] = {
    "mcp_discovery_overhead": SignalOverlay(
        "agent_tooling", "configure_agent_tools", "operational_overhead"
    ),
    "mcp_context_budget_overflow": SignalOverlay(
        "agent_tooling", "configure_agent_tools", "operational_risk"
    ),
    "llm_guardrail_engineering_tax": SignalOverlay(
        "model_operations", "operate_llm_systems", "innovation_blocked"
    ),
    "ai_eval_pipeline_gap": SignalOverlay(
        "llm_evaluation", "evaluate_model_quality", "operational_overhead"
    ),
    "inference_cost_governance": SignalOverlay(
        "inference_governance", "govern_inference_spend", "margin_erosion"
    ),
    "coding_agent_api_spec_gap": SignalOverlay(
        "api_platform", "publish_consume_apis", "operational_risk"
    ),
    "vulnerability_disclosure_workflow": SignalOverlay(
        "vulnerability_management", "remediate_vulnerabilities", "trust_erosion"
    ),
    "incident_response_coordination": SignalOverlay(
        "incident_response", "respond_to_incidents", "trust_erosion"
    ),
    "session_fixation_exposure": SignalOverlay(
        "application_security", "secure_applications", "operational_risk"
    ),
    "endpoint_security_negligence": SignalOverlay(
        "vulnerability_management", "remediate_vulnerabilities", "operational_risk"
    ),
    "cicd_yaml_complexity": SignalOverlay("ci_cd", "deploy_software", "operational_overhead"),
    "pipeline_template_rigidity": SignalOverlay("ci_cd", "deploy_software", "operational_risk"),
    "local_dev_performance": SignalOverlay("deployment", "deploy_software", "operational_risk"),
    "openapi_spec_friction": SignalOverlay(
        "api_platform", "publish_consume_apis", "operational_overhead"
    ),
    "platform_api_dx_friction": SignalOverlay(
        "internal_platform", "operate_internal_platforms", "engineering_friction"
    ),
    "agentic_code_trust_gap": SignalOverlay(
        "developer_experience", "improve_developer_workflow", "operational_risk"
    ),
}


def _resolve_gpu_compute_overlay(*, verbatim_quote: str, summary: str) -> SignalOverlay:
    text = f"{verbatim_quote} {summary}".lower()
    if "quota" in text or "colab" in text:
        return SignalOverlay("capacity_management", "manage_capacity_quotas", "operational_overhead")
    return SignalOverlay("gpu_compute", "provision_compute", "operational_risk")


def resolve_overlay_signals(
    mechanism_fingerprint: str,
    *,
    verbatim_quote: str = "",
    summary: str = "",
) -> SignalOverlay | None:
    if mechanism_fingerprint == "gpu_compute_access_unreliability":
        return _resolve_gpu_compute_overlay(verbatim_quote=verbatim_quote, summary=summary)
    return SIGNAL_OVERLAY_MAP.get(mechanism_fingerprint)


def _needs_signal_overlay(member: ComplaintEvidence) -> bool:
    mechanism = member.mechanism_fingerprint
    if mechanism is None or mechanism in FINTECH_MECHANISMS:
        return False
    if resolve_overlay_signals(
        mechanism,
        verbatim_quote=member.verbatim_quote,
        summary=member.summary,
    ) is None:
        return False

    if has_cross_domain_signal_leakage(
        business_function_code=member.business_function_code,
        jtbd_code=member.jtbd_code,
    ):
        return True

    return not signal_mechanism_coherent(member.business_function_code, mechanism)


def apply_signal_overlay(evidence: ComplaintEvidence) -> ComplaintEvidence:
    """Apply in-memory signal overlay when mechanism and stored signals are incoherent."""
    if not _needs_signal_overlay(evidence):
        return evidence

    overlay = resolve_overlay_signals(
        evidence.mechanism_fingerprint or "",
        verbatim_quote=evidence.verbatim_quote,
        summary=evidence.summary,
    )
    if overlay is None:
        return evidence

    logger.info(
        "signal_overlay_applied",
        extra={
            "complaint_id": str(evidence.id),
            "mechanism_fingerprint": evidence.mechanism_fingerprint,
            "from_business_function_code": evidence.business_function_code,
            "from_jtbd_code": evidence.jtbd_code,
            "from_consequence_code": evidence.consequence_code,
            "to_business_function_code": overlay.business_function_code,
            "to_jtbd_code": overlay.jtbd_code,
            "to_consequence_code": overlay.consequence_code,
        },
    )

    return evidence.model_copy(
        update={
            "business_function_code": overlay.business_function_code,
            "jtbd_code": overlay.jtbd_code,
            "consequence_code": overlay.consequence_code,
            "signal_overlay_applied": True,
        }
    )


def enrich_complaint_evidence_with_overlay(evidence: ComplaintEvidence) -> ComplaintEvidence:
    """Attach mechanism fingerprint, then apply signal overlay when warranted."""
    from app.agents.opportunity.mechanism_fingerprints import enrich_complaint_evidence

    return apply_signal_overlay(enrich_complaint_evidence(evidence))
