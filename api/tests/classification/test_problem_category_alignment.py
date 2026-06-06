"""Tests for problem_category namespace alignment and normalization."""

import pytest

from app.agents.classification.problem_category_alignment import (
    INVALID_PROBLEM_CATEGORY_ALIASES,
    alignment_prompt_block,
    normalize_problem_category,
)
from app.agents.classification.schemas import ClassificationLLMOutput
from app.agents.classification.validator import ClassificationValidator


def _output(**overrides) -> ClassificationLLMOutput:
    payload = {
        "is_complaint": True,
        "industry": "fintech",
        "customer_type": "founder",
        "problem_category": "pricing",
        "severity_score": 4,
        "summary": "Placeholder summary for classification alignment tests.",
        "verbatim_quote": "Placeholder quote for classification alignment tests.",
        "confidence": 0.9,
        "business_function_code": "payment_processor",
        "jtbd_code": "accept_payments",
        "consequence_code": "revenue_interruption",
    }
    payload.update(overrides)
    return ClassificationLLMOutput(**payload)


def test_alignment_prompt_forbids_billing_namespace_leaks() -> None:
    block = alignment_prompt_block()
    assert "problem_category must NEVER be 'billing'" in block
    assert "billing_operations" in block
    assert "two separate code namespaces" in block


@pytest.mark.parametrize(
    ("quote", "summary", "expected"),
    [
        (
            "I just got kicked off Stripe; classified as high risk.",
            "Founder removed from Stripe and needs SaaS billing alternatives.",
            "security",
        ),
        (
            "Stripe billing fees are killing margins.",
            "Payment fees erode margin on every transaction.",
            "pricing",
        ),
        (
            "We need usage-based billing support Stripe does not allow.",
            "Missing usage-based billing capability per subscription.",
            "missing_feature",
        ),
        (
            "Clients never pay invoices on time.",
            "Invoice collection workflow breaks when clients delay payment.",
            "workflow",
        ),
    ],
)
def test_normalize_problem_category_mapping_cases(
    quote: str,
    summary: str,
    expected: str,
) -> None:
    assert (
        normalize_problem_category(
            "billing",
            summary=summary,
            verbatim_quote=quote,
        )
        == expected
    )


def test_normalize_billing_operations_never_persists_as_problem_category() -> None:
    normalized = normalize_problem_category(
        "billing_operations",
        summary="Invoice collection is a monthly headache.",
        verbatim_quote="I have a problem with invoices at the end of the month.",
    )
    assert normalized != "billing_operations"
    assert normalized in {"workflow", "missing_feature", "security", "pricing"}


def test_validator_normalizes_billing_before_taxonomy_check() -> None:
    output = _output(
        problem_category="billing",
        summary="Founder was kicked off Stripe as high risk.",
        verbatim_quote="I just got kicked off Stripe; classified as high risk.",
        business_function_code="payment_processor",
        jtbd_code="accept_payments",
        consequence_code="revenue_interruption",
    )
    source = (
        "Ask HN: Kicked off Stripe. "
        "I just got kicked off Stripe; classified as high risk. Where else can I go?"
    )
    validated = ClassificationValidator().validate(output, source_text=source)
    assert validated.problem_category == "security"
    assert validated.problem_category not in INVALID_PROBLEM_CATEGORY_ALIASES


def test_validator_normalizes_billing_operations_to_workflow() -> None:
    output = _output(
        problem_category="billing_operations",
        summary="Monthly invoice collection creates operational overhead.",
        verbatim_quote="Clients never pay invoices on time.",
        business_function_code="invoice_collection",
        jtbd_code="collect_invoices",
        consequence_code="operational_overhead",
    )
    validated = ClassificationValidator().validate(
        output,
        source_text="Clients never pay invoices on time.",
    )
    assert validated.problem_category == "workflow"
    assert validated.problem_category != "billing_operations"
