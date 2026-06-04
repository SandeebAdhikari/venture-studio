"""Unit tests for opportunity generator graph retry behavior."""

from uuid import uuid4

import pytest

from app.agents.opportunity.graph import OpportunityGeneratorAgent
from app.agents.opportunity.mock_client import MockOpportunityLLMClient
from app.agents.opportunity.schemas import ComplaintEvidence, ComplaintPattern, OpportunityLLMOutput
from app.config import Settings


def _pattern(*, topic: str = "Staff Scheduling", anchor: str = "staff scheduling") -> ComplaintPattern:
    return ComplaintPattern(
        topic=topic,
        anchor_phrase=anchor,
        complaint_ids=[uuid4()],
        domain_code="saas_b2b",
        category_code="workflow",
        dominant_persona_code="ops_admin",
        complaint_count=3,
        avg_severity=4.0,
    )


def _evidence() -> list[ComplaintEvidence]:
    quote = "Staff scheduling breaks every week when staff call out sick."
    return [
        ComplaintEvidence(
            id=uuid4(),
            summary=quote,
            verbatim_quote=quote,
            severity=4,
            domain_code="saas_b2b",
            category_code="workflow",
            persona_code="ops_admin",
            product_mentions=["ShiftApp"],
        )
    ]


def _valid_output() -> OpportunityLLMOutput:
    return OpportunityLLMOutput(
        title="Staff Scheduling SaaS",
        problem_statement=(
            "Operations teams repeatedly struggle with staff scheduling across shifts "
            "and last-minute callouts."
        ),
        target_user="Ops admins managing hourly staff",
        frequency_signal="Multiple complaints mention staff scheduling friction.",
        existing_alternatives="Teams mention ShiftApp in the evidence.",
        gap="No purpose-built scheduling workflow for shift-based teams.",
        confidence_score=0.82,
        explanation="Recurring staff scheduling complaints indicate a focused SaaS wedge.",
    )


@pytest.mark.asyncio
async def test_retry_passes_validation_errors_to_llm() -> None:
    bad = _valid_output().model_copy(
        update={"existing_alternatives": "Teams rely on MegaCorp Scheduler Pro."}
    )
    mock = MockOpportunityLLMClient([bad, _valid_output()])
    settings = Settings(
        api_key="test-api-key-for-graph",
        generation_max_retries=2,
        min_opportunity_confidence=0.4,
        generation_model="mock-generator",
    )
    agent = OpportunityGeneratorAgent(mock, settings)

    result = await agent.run(_pattern(), _evidence())

    assert result.status == "created"
    assert mock.call_count == 2
    assert mock.last_validation_errors is not None
    assert any("ungrounded product" in err for err in mock.last_validation_errors)
