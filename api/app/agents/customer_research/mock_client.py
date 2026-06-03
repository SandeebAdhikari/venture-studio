"""Mock LLM client for customer research tests."""

from __future__ import annotations

from uuid import UUID

from app.agents.customer_research.llm_client import LLMInvocationResult
from app.agents.customer_research.schemas import (
    CustomerResearchLLMOutput,
    OpportunityCustomerContext,
    RepresentativeComplaintOutput,
    SupportingEvidenceOutput,
)


class MockCustomerResearchLLMClient:
    """Returns scripted customer research responses in call order."""

    def __init__(
        self,
        responses: list[CustomerResearchLLMOutput | None] | dict[UUID, CustomerResearchLLMOutput],
        *,
        model: str = "mock-customer-research",
    ) -> None:
        if isinstance(responses, dict):
            self._by_opportunity = responses
            self._responses: list[CustomerResearchLLMOutput | None] = []
        else:
            self._by_opportunity = {}
            self._responses = list(responses)
        self._index = 0
        self._model = model
        self.call_count = 0

    async def research(
        self,
        *,
        context: OpportunityCustomerContext,
        attempt: int,
    ) -> LLMInvocationResult:
        del attempt
        self.call_count += 1
        response: CustomerResearchLLMOutput | None = None

        if context.opportunity_id in self._by_opportunity:
            response = self._by_opportunity[context.opportunity_id]
        elif self._index < len(self._responses):
            response = self._responses[self._index]
            self._index += 1

        if response is None:
            return LLMInvocationResult(
                parsed=None,
                raw_text="not valid json",
                model=self._model,
                error="no_more_mock_responses",
            )

        return LLMInvocationResult(
            parsed=response,
            raw_text=response.model_dump_json(),
            model=self._model,
            prompt_tokens=320,
            completion_tokens=200,
            latency_ms=22,
            cost_usd=0.0,
        )


def default_mock_customer_research_output() -> CustomerResearchLLMOutput:
    """Standard mock customer research for scheduling pain opportunities."""
    quote = "Staff scheduling breaks every week when employees swap shifts without notice."
    return CustomerResearchLLMOutput(
        pain_score=82,
        urgency_score=76,
        frequency_score=88,
        customer_sentiment="negative",
        sentiment_score=-0.65,
        cares_verdict="yes",
        representative_complaints=[
            RepresentativeComplaintOutput(
                summary="Staff scheduling chaos from last-minute shift changes.",
                verbatim_quote=quote,
                severity=4,
                source_type="forum",
                complaint_index=0,
            ),
        ],
        supporting_evidence=[
            SupportingEvidenceOutput(
                evidence_type="forum",
                excerpt=quote,
                source_reference="Reddit r/SaaS discussion thread",
                supports_conclusion="pain",
                confidence="high",
                complaint_index=0,
            ),
            SupportingEvidenceOutput(
                evidence_type="complaint",
                excerpt="Managers rebuild schedules manually after call-outs.",
                source_reference="Linked opportunity complaint evidence",
                supports_conclusion="urgency",
                confidence="high",
                complaint_index=0,
            ),
            SupportingEvidenceOutput(
                evidence_type="discussion",
                excerpt="Recurring staff scheduling complaints across multiple posts.",
                source_reference="Aggregated complaint pattern",
                supports_conclusion="frequency",
                confidence="medium",
                complaint_index=0,
            ),
        ],
        executive_summary=(
            "Customers clearly care about staff scheduling pain. Evidence shows high "
            "frequency of complaints, strong negative sentiment, and urgent operational "
            "impact when shifts change without notice."
        ),
    )
