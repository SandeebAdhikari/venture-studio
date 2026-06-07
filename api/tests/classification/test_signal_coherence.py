"""Tests for signal–mechanism coherence detection."""

import pytest

from app.agents.classification.signal_coherence import (
    has_cross_domain_signal_leakage,
    incoherence_reason,
    signal_mechanism_coherent,
)


@pytest.mark.parametrize(
    ("bf", "jtbd", "expected"),
    [
        ("payment_processor", "accept_payments", True),
        ("fraud_prevention", "prevent_fraud", True),
        ("agent_tooling", "configure_agent_tools", False),
    ],
)
def test_cross_domain_leakage_detection(bf: str, jtbd: str, expected: bool) -> None:
    assert (
        has_cross_domain_signal_leakage(
            business_function_code=bf,
            jtbd_code=jtbd,
        )
        is expected
    )


@pytest.mark.parametrize(
    ("bf", "mechanism", "expected"),
    [
        ("gpu_compute", "gpu_compute_access_unreliability", True),
        ("payment_processor", "gpu_compute_access_unreliability", False),
        ("agent_tooling", "mcp_discovery_overhead", True),
        ("observability", "mcp_discovery_overhead", False),
        ("vulnerability_management", "vulnerability_disclosure_workflow", True),
        ("fraud_prevention", "vulnerability_disclosure_workflow", False),
        ("payment_processor", "processor_account_deplatforming", True),
    ],
)
def test_signal_mechanism_coherent(bf: str, mechanism: str, expected: bool) -> None:
    assert signal_mechanism_coherent(bf, mechanism) is expected


def test_incoherence_reason_for_fintech_on_ai_mechanism() -> None:
    assert (
        incoherence_reason(
            business_function_code="payment_processor",
            jtbd_code="accept_payments",
            mechanism_fingerprint="gpu_compute_access_unreliability",
        )
        == "cross_domain_fintech_signal"
    )


def test_incoherence_reason_none_for_coherent_pair() -> None:
    assert (
        incoherence_reason(
            business_function_code="llm_evaluation",
            jtbd_code="evaluate_model_quality",
            mechanism_fingerprint="ai_eval_pipeline_gap",
        )
        is None
    )
