"""Tests for founder signal enum validation."""

import pytest

from app.agents.classification.founder_signals import (
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
