"""Tests for founder signal enum validation."""

import pytest

from app.agents.classification.founder_signals import (
    BUSINESS_FUNCTION_CODES,
    CONSEQUENCE_CODES,
    JTBD_CODES,
    validate_business_function_code,
    validate_consequence_code,
    validate_founder_signal_codes,
    validate_jtbd_code,
)
from app.agents.classification.schemas import ClassificationLLMOutput
from app.agents.classification.validator import ClassificationValidationError, ClassificationValidator


def test_validate_founder_signal_codes_accepts_known_values() -> None:
    result = validate_founder_signal_codes(
        business_function_code="payment_processor",
        jtbd_code="accept_payments",
        consequence_code="revenue_interruption",
    )
    assert result == ("payment_processor", "accept_payments", "revenue_interruption")


def test_validate_founder_signal_codes_rejects_unknown_values() -> None:
    assert validate_business_function_code("general_frustration") is None
    assert validate_jtbd_code("grow_revenue") is None
    assert validate_consequence_code("other") is None
    assert (
        validate_founder_signal_codes(
            business_function_code="general_frustration",
            jtbd_code="accept_payments",
            consequence_code="revenue_interruption",
        )
        is None
    )


@pytest.mark.parametrize(
    "code",
    [
        "agent_tooling",
        "model_operations",
        "gpu_compute",
        "vulnerability_management",
        "developer_experience",
        "api_platform",
        "capacity_management",
    ],
)
def test_v2_business_function_codes_accepted(code: str) -> None:
    assert validate_business_function_code(code) == code
    assert code in BUSINESS_FUNCTION_CODES


@pytest.mark.parametrize(
    "code",
    [
        "configure_agent_tools",
        "operate_llm_systems",
        "evaluate_model_quality",
        "remediate_vulnerabilities",
        "publish_consume_apis",
        "manage_capacity_quotas",
    ],
)
def test_v2_jtbd_codes_accepted(code: str) -> None:
    assert validate_jtbd_code(code) == code
    assert code in JTBD_CODES


@pytest.mark.parametrize("code", ["trust_erosion", "innovation_blocked"])
def test_v2_consequence_codes_accepted(code: str) -> None:
    assert validate_consequence_code(code) == code
    assert code in CONSEQUENCE_CODES


def test_v1_codes_remain_valid() -> None:
    assert validate_founder_signal_codes(
        business_function_code="payment_processor",
        jtbd_code="accept_payments",
        consequence_code="revenue_interruption",
    ) == ("payment_processor", "accept_payments", "revenue_interruption")


def test_validator_rejects_invalid_founder_signal_codes() -> None:
    output = ClassificationLLMOutput(
        is_complaint=True,
        industry="fintech",
        customer_type="founder",
        problem_category="pricing",
        severity_score=4,
        summary="The billing processor was removed and revenue collection stopped.",
        verbatim_quote="billing processor was removed",
        confidence=0.9,
        business_function_code="unknown_function",
        jtbd_code="accept_payments",
        consequence_code="revenue_interruption",
    )
    with pytest.raises(ClassificationValidationError) as exc:
        ClassificationValidator().validate(
            output,
            source_text="The billing processor was removed and revenue collection stopped.",
        )
    assert any("invalid founder signal codes" in err for err in exc.value.errors)
