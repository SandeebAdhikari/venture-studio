"""Tests for ALLOWED_BF_JTBD_PAIRS matrix."""

import pytest

from app.agents.classification.founder_signal_pairs import (
    ALLOWED_BF_JTBD_PAIRS,
    validate_bf_jtbd_pair,
)


@pytest.mark.parametrize(
    ("bf", "jtbd"),
    [
        ("payment_processor", "accept_payments"),
        ("fraud_prevention", "prevent_fraud"),
        ("agent_tooling", "configure_agent_tools"),
        ("model_operations", "operate_llm_systems"),
        ("gpu_compute", "provision_compute"),
        ("vulnerability_management", "remediate_vulnerabilities"),
        ("application_security", "secure_applications"),
        ("api_platform", "publish_consume_apis"),
        ("capacity_management", "manage_capacity_quotas"),
    ],
)
def test_allowed_pairs_accepted(bf: str, jtbd: str) -> None:
    assert validate_bf_jtbd_pair(bf, jtbd) is True
    assert jtbd in ALLOWED_BF_JTBD_PAIRS[bf]


@pytest.mark.parametrize(
    ("bf", "jtbd"),
    [
        ("payment_processor", "configure_agent_tools"),
        ("fraud_prevention", "remediate_vulnerabilities"),
        ("agent_tooling", "accept_payments"),
        ("gpu_compute", "manage_subscriptions"),
        ("vulnerability_management", "prevent_fraud"),
        ("observability", "accept_payments"),
    ],
)
def test_incoherent_pairs_rejected(bf: str, jtbd: str) -> None:
    assert validate_bf_jtbd_pair(bf, jtbd) is False


def test_unknown_business_function_rejected() -> None:
    assert validate_bf_jtbd_pair("unknown_bf", "accept_payments") is False
