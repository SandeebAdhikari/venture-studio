"""Tests for customer research LangGraph retry and validation flow."""

from uuid import uuid4

import pytest

from app.agents.customer_research.graph import CustomerResearchAgent
from app.agents.customer_research.mock_client import MockCustomerResearchLLMClient
from app.agents.customer_research.schemas import (
    ComplaintEvidenceItem,
    CustomerResearchLLMOutput,
    OpportunityCustomerContext,
    RepresentativeComplaintOutput,
    SupportingEvidenceOutput,
)
from app.config import Settings


def _context() -> OpportunityCustomerContext:
    quote = "Build pipelines fail when node versions drift between machines."
    return OpportunityCustomerContext(
        opportunity_id=uuid4(),
        title="CI environment drift",
        problem_statement="Teams cannot keep dev environments aligned.",
        target_user="Platform engineers",
        frequency_signal="Multiple threads mention drift.",
        gap="No drift detection layer",
        confidence_score=0.77,
        complaint_evidence=[
            ComplaintEvidenceItem(
                index=0,
                complaint_id=uuid4(),
                signal_id=uuid4(),
                summary="Node version drift breaks builds.",
                verbatim_quote=quote,
                severity=4,
                source_type="discussion",
                source_name="hn-saas",
                url="https://news.ycombinator.com/item?id=1",
            )
        ],
    )


def _minimal_supporting(quote: str) -> list[SupportingEvidenceOutput]:
    return [
        SupportingEvidenceOutput(
            evidence_type="discussion",
            excerpt=quote[:40],
            source_reference="HN",
            supports_conclusion="pain",
            confidence="high",
            complaint_index=0,
        )
    ]


def _output_with_quote(*, quote: str, summary_len: int = 80) -> CustomerResearchLLMOutput:
    return CustomerResearchLLMOutput(
        pain_score=75,
        urgency_score=70,
        frequency_score=65,
        customer_sentiment="negative",
        sentiment_score=-0.6,
        cares_verdict="yes",
        representative_complaints=[
            RepresentativeComplaintOutput(
                summary="Build failures from environment drift.",
                verbatim_quote=quote,
                severity=4,
                source_type="discussion",
                complaint_index=0,
            )
        ],
        supporting_evidence=_minimal_supporting(quote),
        executive_summary="x" * summary_len,
    )


@pytest.mark.asyncio
async def test_graph_completes_when_llm_paraphrases_but_index_valid() -> None:
    """Canonicalization should prevent retry loops on paraphrased quotes."""
    context = _context()
    evidence_quote = context.complaint_evidence[0].verbatim_quote
    client = MockCustomerResearchLLMClient(
        [_output_with_quote(quote="Completely paraphrased drift pain.")]
    )
    settings = Settings(
        api_key="test-api-key-for-customer-research-graph",
        customer_research_model="mock-customer-research",
        customer_research_max_retries=2,
    )
    agent = CustomerResearchAgent(client, settings)

    result = await agent.run(context)

    assert result.status == "completed"
    assert result.draft is not None
    assert result.draft.representative_complaints[0].verbatim_quote == evidence_quote
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_graph_retries_then_completes_after_valid_second_response() -> None:
    context = _context()
    evidence_quote = context.complaint_evidence[0].verbatim_quote
    bad = _output_with_quote(quote="x", summary_len=10)
    good = _output_with_quote(quote="Still paraphrased but indexed.", summary_len=80)
    client = MockCustomerResearchLLMClient([bad, good])
    settings = Settings(
        api_key="test-api-key-for-customer-research-graph",
        customer_research_model="mock-customer-research",
        customer_research_max_retries=2,
    )
    agent = CustomerResearchAgent(client, settings)

    result = await agent.run(context)

    assert result.status == "completed"
    assert result.draft is not None
    assert result.draft.representative_complaints[0].verbatim_quote == evidence_quote
    assert client.call_count == 2
