"""Unit tests for customer research validator."""

from uuid import uuid4

import pytest

from app.agents.customer_research.metrics import compute_validation_metrics
from app.agents.customer_research.mock_client import default_mock_customer_research_output
from app.agents.customer_research.schemas import ComplaintEvidenceItem, OpportunityCustomerContext
from app.agents.customer_research.validator import (
    CustomerResearchValidationError,
    CustomerResearchValidator,
)

QUOTE = "Staff scheduling breaks every week when employees swap shifts without notice."


def _context() -> OpportunityCustomerContext:
    complaint_id = uuid4()
    signal_id = uuid4()
    return OpportunityCustomerContext(
        opportunity_id=uuid4(),
        title="Staff Scheduling SaaS",
        problem_statement="Ops teams struggle with hourly staff scheduling.",
        target_user="Ops admins",
        frequency_signal="Repeated scheduling complaints.",
        gap="No lightweight scheduling workflow.",
        confidence_score=0.86,
        complaint_evidence=[
            ComplaintEvidenceItem(
                index=0,
                complaint_id=complaint_id,
                signal_id=signal_id,
                summary="Staff scheduling chaos from last-minute shift changes.",
                verbatim_quote=QUOTE,
                severity=4,
                source_type="forum",
                source_name="reddit-saas",
                url="https://example.com/post/1",
            )
        ],
    )


def test_validator_accepts_valid_output() -> None:
    validator = CustomerResearchValidator()
    output = default_mock_customer_research_output()
    result = validator.validate(output, context=_context())
    assert result.cares_verdict == "yes"


def test_validator_rejects_inconsistent_sentiment() -> None:
    validator = CustomerResearchValidator()
    output = default_mock_customer_research_output()
    output.customer_sentiment = "positive"
    output.sentiment_score = -0.8
    with pytest.raises(CustomerResearchValidationError) as exc_info:
        validator.validate(output, context=_context())
    assert any("sentiment_score inconsistent" in error for error in exc_info.value.errors)


def test_validation_metrics_include_readiness_score() -> None:
    output = default_mock_customer_research_output()
    metrics = compute_validation_metrics(output, context=_context(), linked_complaint_count=1)
    assert metrics["cares_verdict"] == "yes"
    assert metrics["validation_readiness_score"] > 0
