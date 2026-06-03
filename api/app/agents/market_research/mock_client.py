"""Mock LLM client for market research tests."""

from __future__ import annotations

from uuid import UUID

from app.agents.market_research.llm_client import LLMInvocationResult
from app.agents.market_research.schemas import (
    CustomerSegment,
    IndustryTrend,
    MarketResearchLLMOutput,
    OpportunityResearchContext,
    SupportingEvidence,
)


class MockMarketResearchLLMClient:
    """Returns scripted market research responses in call order or by opportunity ID."""

    def __init__(
        self,
        responses: list[MarketResearchLLMOutput | None] | dict[UUID, MarketResearchLLMOutput],
        *,
        model: str = "mock-research",
    ) -> None:
        if isinstance(responses, dict):
            self._by_opportunity = responses
            self._responses: list[MarketResearchLLMOutput | None] = []
        else:
            self._by_opportunity = {}
            self._responses = list(responses)
        self._index = 0
        self._model = model
        self.call_count = 0

    async def research(
        self,
        *,
        context: OpportunityResearchContext,
        attempt: int,
    ) -> LLMInvocationResult:
        del attempt
        self.call_count += 1
        response: MarketResearchLLMOutput | None = None

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
            prompt_tokens=300,
            completion_tokens=180,
            latency_ms=20,
            cost_usd=0.0,
        )


def default_mock_research_output() -> MarketResearchLLMOutput:
    """Standard mock market intelligence for scheduling SaaS opportunities."""
    return MarketResearchLLMOutput(
        market_size_usd=12_000_000_000,
        tam_usd=4_500_000_000,
        sam_usd=900_000_000,
        industry_growth_rate_pct=8.5,
        customer_segments=[
            CustomerSegment(
                name="Multi-location retail ops",
                description="Regional chains with hourly staff across 5-50 locations.",
                estimated_share_pct=35.0,
            ),
            CustomerSegment(
                name="Healthcare clinics",
                description="Outpatient clinics coordinating nurse and admin shifts.",
                estimated_share_pct=25.0,
            ),
        ],
        industry_trends=[
            IndustryTrend(
                trend="Workforce management digitization",
                description="SMBs are replacing spreadsheets with cloud scheduling tools.",
                relevance="Increases willingness to pay for lightweight scheduling SaaS.",
            ),
            IndustryTrend(
                trend="Labor shortage pressure",
                description="Tight labor markets increase the cost of scheduling errors.",
                relevance="Heightens urgency for tools that reduce coverage gaps.",
            ),
        ],
        supporting_evidence=[
            SupportingEvidence(
                claim="Workforce management software market exceeds $10B globally.",
                source_type="public_market_data",
                source_reference="Industry analyst workforce management market estimates",
                confidence="medium",
            ),
            SupportingEvidence(
                claim="Recurring staff scheduling complaints indicate persistent SMB pain.",
                source_type="inference_from_complaints",
                source_reference="Linked opportunity complaint summaries",
                confidence="high",
            ),
        ],
        executive_summary=(
            "Staff scheduling for hourly-workforce SMBs sits in a large and growing "
            "workforce management market. The serviceable segment for lightweight SaaS "
            "focused on multi-location ops is substantial, with digitization and labor "
            "shortages reinforcing demand."
        ),
    )
