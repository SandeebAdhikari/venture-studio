"""Unit tests for classification output validation."""

import pytest

from app.agents.classification.schemas import ClassificationLLMOutput
from app.agents.classification.validator import (
    ClassificationValidationError,
    ClassificationValidator,
)


def _output(**overrides) -> ClassificationLLMOutput:
    payload = {
        "is_complaint": True,
        "industry": "saas_b2b",
        "customer_type": "founder",
        "problem_category": "pricing",
        "severity_score": 3,
        "summary": "The pricing model is too expensive for early-stage teams.",
        "verbatim_quote": "pricing is too expensive",
        "confidence": 0.8,
    }
    payload.update(overrides)
    return ClassificationLLMOutput(**payload)


def test_validator_accepts_valid_output() -> None:
    output = _output()
    source = "The pricing is too expensive for us."
    validated = ClassificationValidator().validate(output, source_text=source)
    assert validated.problem_category == "pricing"


def test_validator_rejects_invalid_taxonomy() -> None:
    output = _output(industry="not_real")
    source = "The pricing is too expensive for us."
    with pytest.raises(ClassificationValidationError) as exc:
        ClassificationValidator().validate(output, source_text=source)
    assert any("invalid industry" in err for err in exc.value.errors)


def test_validator_rejects_quote_not_in_source() -> None:
    output = _output(verbatim_quote="this quote is missing")
    with pytest.raises(ClassificationValidationError) as exc:
        ClassificationValidator().validate(
            output,
            source_text="Totally different source text here.",
        )
    assert any("verbatim_quote" in err for err in exc.value.errors)


def test_validator_accepts_quote_after_html_normalization() -> None:
    from app.agents.classification.source_text import build_classification_source_text

    source = build_classification_source_text(
        title=None,
        body="I can&#x27;t install all these <i>packages</i> reliably.",
    )
    output = _output(verbatim_quote="I can't install all these packages reliably.")
    validated = ClassificationValidator().validate(output, source_text=source)
    assert validated.verbatim_quote.startswith("I can't")


def test_validator_rejects_invalid_customer_type_employee() -> None:
    output = _output(customer_type="employee")
    with pytest.raises(ClassificationValidationError) as exc:
        ClassificationValidator().validate(
            output,
            source_text="pricing is too expensive for our team",
        )
    assert any("invalid customer_type" in err for err in exc.value.errors)
    assert not any("verbatim_quote" in err for err in exc.value.errors)
