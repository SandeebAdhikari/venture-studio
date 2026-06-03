"""Mock LLM client for competitor intelligence tests."""

from __future__ import annotations

from uuid import UUID

from app.agents.competitor_intelligence.llm_client import LLMInvocationResult
from app.agents.competitor_intelligence.schemas import (
    CompetitorAnalysisLLMOutput,
    CompetitorPricingModel,
    CompetitorProfileOutput,
    CompetitiveGap,
    CustomerComplaintSummary,
    OpportunityCompetitorContext,
)


class MockCompetitorIntelligenceLLMClient:
    """Returns scripted competitor analysis responses in call order or by opportunity ID."""

    def __init__(
        self,
        responses: list[CompetitorAnalysisLLMOutput | None] | dict[UUID, CompetitorAnalysisLLMOutput],
        *,
        model: str = "mock-competitor",
    ) -> None:
        if isinstance(responses, dict):
            self._by_opportunity = responses
            self._responses: list[CompetitorAnalysisLLMOutput | None] = []
        else:
            self._by_opportunity = {}
            self._responses = list(responses)
        self._index = 0
        self._model = model
        self.call_count = 0

    async def analyze(
        self,
        *,
        context: OpportunityCompetitorContext,
        attempt: int,
    ) -> LLMInvocationResult:
        del attempt
        self.call_count += 1
        response: CompetitorAnalysisLLMOutput | None = None

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
            prompt_tokens=350,
            completion_tokens=220,
            latency_ms=25,
            cost_usd=0.0,
        )


def default_mock_competitor_output() -> CompetitorAnalysisLLMOutput:
    """Standard mock competitor intelligence for scheduling SaaS opportunities."""
    return CompetitorAnalysisLLMOutput(
        competitors=[
            CompetitorProfileOutput(
                name="ShiftApp",
                positioning="Mid-market workforce scheduling for retail and hospitality teams.",
                pricing=CompetitorPricingModel(
                    model_type="subscription",
                    starting_price_usd=8.0,
                    billing_period="per_user_monthly",
                    pricing_notes=(
                        "Published per-user monthly pricing with tiered plans for multi-location teams."
                    ),
                ),
                strengths=[
                    "Established brand in hourly workforce scheduling",
                    "Mobile apps for shift swaps",
                ],
                weaknesses=[
                    "Complex setup for small teams",
                    "Limited last-minute coverage automation",
                ],
                customer_complaints=[
                    CustomerComplaintSummary(
                        summary="Users report painful shift swap workflows on mobile.",
                        theme="shift_swapping",
                        sentiment="negative",
                    ),
                    CustomerComplaintSummary(
                        summary="Managers rebuild schedules manually after call-outs.",
                        theme="manual_rebuilds",
                        sentiment="negative",
                    ),
                ],
                review_sentiment="mixed",
                sentiment_score=-0.2,
                source_basis="Mentioned in opportunity complaint evidence",
            ),
            CompetitorProfileOutput(
                name="WhenIWork",
                positioning="SMB-focused employee scheduling and time tracking.",
                pricing=CompetitorPricingModel(
                    model_type="freemium",
                    starting_price_usd=2.5,
                    billing_period="per_user_monthly",
                    pricing_notes="Free tier for small teams; paid plans add automation features.",
                ),
                strengths=[
                    "Low entry price for small teams",
                    "Simple onboarding",
                ],
                weaknesses=[
                    "Limited multi-location coordination",
                    "Basic reporting for ops managers",
                ],
                customer_complaints=[
                    CustomerComplaintSummary(
                        summary="Multi-location teams outgrow reporting quickly.",
                        theme="reporting_limits",
                        sentiment="mixed",
                    ),
                ],
                review_sentiment="neutral",
                sentiment_score=0.0,
                source_basis="Category knowledge for SMB scheduling tools",
            ),
        ],
        competitive_gaps=[
            CompetitiveGap(
                gap="Lightweight hourly-staff coordination",
                description=(
                    "Existing tools skew enterprise-heavy or lack automated coverage recovery "
                    "for multi-location hourly teams."
                ),
                opportunity_angle=(
                    "Focus on fast setup, call-out recovery, and manager-friendly scheduling "
                    "for 5-50 location SMBs."
                ),
                affected_competitors=["ShiftApp", "WhenIWork"],
            ),
        ],
        executive_summary=(
            "The scheduling market includes established players like ShiftApp and WhenIWork, "
            "both with mixed-to-neutral sentiment around complexity and multi-location gaps. "
            "A lightweight wedge focused on hourly coordination and call-out recovery has room "
            "against incumbents optimized for broader workforce management."
        ),
    )
