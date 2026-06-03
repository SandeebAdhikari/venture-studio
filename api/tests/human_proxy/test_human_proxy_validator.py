"""Unit tests for human proxy validator and metrics."""

from uuid import uuid4

import pytest

from app.agents.human_proxy.metrics import compute_evaluation_metrics
from app.agents.human_proxy.mock_client import default_mock_human_proxy_output
from app.agents.human_proxy.schemas import (
    ComplaintEvidenceItem,
    FounderProfileContext,
    OpportunityProxyContext,
)
from app.agents.human_proxy.validator import HumanProxyValidationError, HumanProxyValidator

QUOTE = "Staff scheduling breaks every week when employees swap shifts without notice."


def _context() -> OpportunityProxyContext:
    complaint_id = uuid4()
    signal_id = uuid4()
    profile_id = uuid4()
    return OpportunityProxyContext(
        opportunity_id=uuid4(),
        title="Staff Scheduling SaaS",
        problem_statement="Ops teams struggle with hourly staff scheduling.",
        target_user="Ops admins",
        frequency_signal="Repeated scheduling complaints.",
        existing_alternatives="ShiftApp and spreadsheets",
        gap="No lightweight scheduling workflow.",
        confidence_score=0.86,
        founder_profile=FounderProfileContext(
            founder_profile_id=profile_id,
            name="Default Solo Technical Founder",
            skills=["Next.js", "TypeScript", "Python", "PostgreSQL"],
            constraints={"team_size": "solo", "budget": "limited", "time": "limited"},
        ),
        complaint_evidence=[
            ComplaintEvidenceItem(
                index=0,
                complaint_id=complaint_id,
                signal_id=signal_id,
                summary="Staff scheduling chaos from last-minute shift changes.",
                verbatim_quote=QUOTE,
                severity=4,
                product_mentions=["ShiftApp"],
            )
        ],
    )


def test_validator_accepts_valid_output() -> None:
    validator = HumanProxyValidator()
    output = default_mock_human_proxy_output()
    result = validator.validate(output, context=_context())
    assert result.founder_fit_score == 82


def test_validator_rejects_pursue_with_low_fit() -> None:
    validator = HumanProxyValidator()
    output = default_mock_human_proxy_output()
    output.recommendation = "pursue"
    output.founder_fit_score = 50
    with pytest.raises(HumanProxyValidationError) as exc_info:
        validator.validate(output, context=_context())
    assert any("founder_fit_score" in error for error in exc_info.value.errors)


def test_validator_rejects_pass_with_high_fit() -> None:
    validator = HumanProxyValidator()
    output = default_mock_human_proxy_output()
    output.recommendation = "pass"
    output.founder_fit_score = 85
    with pytest.raises(HumanProxyValidationError) as exc_info:
        validator.validate(output, context=_context())
    assert any("pass recommendation" in error for error in exc_info.value.errors)


def test_evaluation_metrics_include_ranking_score() -> None:
    output = default_mock_human_proxy_output()
    metrics = compute_evaluation_metrics(output)
    assert metrics["founder_fit_score"] == 82
    assert metrics["feasibility_score"] == 76
    assert metrics["recommendation"] == "pursue"
    assert metrics["ranking_score"] > 0
