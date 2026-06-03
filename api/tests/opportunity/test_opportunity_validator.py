"""Unit tests for opportunity synthesis validation."""

from uuid import uuid4

import pytest

from app.agents.opportunity.schemas import ComplaintEvidence, OpportunityLLMOutput
from app.agents.opportunity.validator import OpportunityValidationError, OpportunityValidator


def _evidence(*, summary: str, products: list[str] | None = None) -> ComplaintEvidence:
    return ComplaintEvidence(
        id=uuid4(),
        summary=summary,
        verbatim_quote=summary,
        severity=4,
        domain_code="saas_b2b",
        category_code="workflow",
        persona_code="ops_admin",
        product_mentions=products or [],
    )


def _output(**overrides) -> OpportunityLLMOutput:
    payload = {
        "title": "Staff Scheduling SaaS",
        "problem_statement": "Teams struggle to coordinate staff scheduling across locations.",
        "target_user": "Ops admins managing hourly staff",
        "frequency_signal": "Multiple complaints mention staff scheduling friction.",
        "existing_alternatives": "Teams mention ShiftApp and spreadsheets in the evidence.",
        "gap": "No purpose-built scheduling workflow for shift-based teams.",
        "confidence_score": 0.82,
        "explanation": "Recurring staff scheduling complaints indicate a focused SaaS wedge.",
    }
    payload.update(overrides)
    return OpportunityLLMOutput(**payload)


def test_validator_accepts_grounded_output() -> None:
    evidence = [
        _evidence(
            summary="Staff scheduling breaks when shifts change.",
            products=["ShiftApp"],
        )
    ]
    validated = OpportunityValidator().validate(
        _output(),
        evidence=evidence,
        topic="Staff Scheduling",
    )
    assert validated.title == "Staff Scheduling SaaS"


def test_validator_rejects_ungrounded_product() -> None:
    evidence = [_evidence(summary="Staff scheduling breaks when shifts change.")]
    with pytest.raises(OpportunityValidationError) as exc:
        OpportunityValidator().validate(
            _output(existing_alternatives="Teams rely on MegaCorp Scheduler Pro."),
            evidence=evidence,
            topic="Staff Scheduling",
        )
    assert any("ungrounded product" in err for err in exc.value.errors)
