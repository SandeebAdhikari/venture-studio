"""Tests for mechanism-to-signal overlays."""

from uuid import uuid4

import pytest

from app.agents.classification.signal_overlays import (
    apply_signal_overlay,
    enrich_complaint_evidence_with_overlay,
)
from app.agents.opportunity.schemas import ComplaintEvidence


def _evidence(**overrides) -> ComplaintEvidence:
    payload = {
        "id": uuid4(),
        "summary": "GPU rental performance does not match console listing.",
        "verbatim_quote": (
            "As a client renting GPUs I've found it to be pretty unreliable compared to "
            "what's listed in the console."
        ),
        "severity": 4,
        "domain_code": "devtools",
        "category_code": "performance",
        "persona_code": "developer",
        "business_function_code": "payment_processor",
        "jtbd_code": "accept_payments",
        "consequence_code": "revenue_interruption",
        "mechanism_fingerprint": "gpu_compute_access_unreliability",
    }
    payload.update(overrides)
    return ComplaintEvidence(**payload)


def test_overlay_corrects_fintech_leakage_on_gpu_mechanism() -> None:
    overlaid = apply_signal_overlay(_evidence())
    assert overlaid.business_function_code == "gpu_compute"
    assert overlaid.jtbd_code == "provision_compute"
    assert overlaid.signal_overlay_applied is True


def test_colab_quota_maps_to_capacity_management() -> None:
    overlaid = apply_signal_overlay(
        _evidence(
            summary="Colab paid options don't work; quota keeps blocking experiments.",
            verbatim_quote="Google Colab paid options don't work and I'm wasting time on quota.",
            mechanism_fingerprint="gpu_compute_access_unreliability",
        )
    )
    assert overlaid.business_function_code == "capacity_management"
    assert overlaid.jtbd_code == "manage_capacity_quotas"


def test_stripe_mechanism_never_overlays() -> None:
    member = _evidence(
        business_function_code="payment_processor",
        jtbd_code="accept_payments",
        consequence_code="revenue_interruption",
        mechanism_fingerprint="processor_account_deplatforming",
        verbatim_quote="I just got kicked off Stripe; classified as high risk.",
        summary="Founder removed from Stripe.",
    )
    overlaid = apply_signal_overlay(member)
    assert overlaid.business_function_code == "payment_processor"
    assert overlaid.signal_overlay_applied is False


def test_coherent_v2_signals_are_not_re_overlaid() -> None:
    member = _evidence(
        business_function_code="agent_tooling",
        jtbd_code="configure_agent_tools",
        consequence_code="operational_overhead",
        mechanism_fingerprint="mcp_discovery_overhead",
        verbatim_quote='This feels incredibly time-consuming and not "agentic".',
        summary="MCP discovery is time-consuming.",
    )
    overlaid = apply_signal_overlay(member)
    assert overlaid.business_function_code == "agent_tooling"
    assert overlaid.signal_overlay_applied is False


@pytest.mark.parametrize(
    ("mechanism", "bf", "jtbd"),
    [
        ("vulnerability_disclosure_workflow", "vulnerability_management", "remediate_vulnerabilities"),
        ("inference_cost_governance", "inference_governance", "govern_inference_spend"),
        ("llm_guardrail_engineering_tax", "model_operations", "operate_llm_systems"),
        ("ai_eval_pipeline_gap", "llm_evaluation", "evaluate_model_quality"),
    ],
)
def test_security_and_ai_overlays_from_fintech_leakage(
    mechanism: str,
    bf: str,
    jtbd: str,
) -> None:
    overlaid = apply_signal_overlay(
        _evidence(
            mechanism_fingerprint=mechanism,
            business_function_code="fraud_prevention",
            jtbd_code="prevent_fraud",
            consequence_code="operational_risk",
            verbatim_quote="Representative quote long enough for specificity gate testing here.",
            summary="Security or AI infra complaint with fintech leakage.",
        )
    )
    assert overlaid.business_function_code == bf
    assert overlaid.jtbd_code == jtbd
    assert overlaid.signal_overlay_applied is True


def test_enrich_with_overlay_attaches_mechanism_then_overlays() -> None:
    member = ComplaintEvidence(
        id=uuid4(),
        summary="Been trying to build a proper evaluation pipeline for months.",
        verbatim_quote=(
            "Been trying to build a proper evaluation pipeline for months but every tool "
            "we've tested has significant limitations."
        ),
        severity=4,
        domain_code="devtools",
        category_code="missing_feature",
        persona_code="developer",
        business_function_code="observability",
        jtbd_code="monitor_systems",
        consequence_code="operational_overhead",
    )
    enriched = enrich_complaint_evidence_with_overlay(member)
    assert enriched.mechanism_fingerprint == "ai_eval_pipeline_gap"
    assert enriched.business_function_code == "llm_evaluation"
    assert enriched.jtbd_code == "evaluate_model_quality"
    assert enriched.signal_overlay_applied is True
