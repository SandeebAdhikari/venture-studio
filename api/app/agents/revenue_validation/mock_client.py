"""Mock LLM client for revenue validation tests."""

from __future__ import annotations

from uuid import UUID

from app.agents.revenue_validation.llm_client import LLMInvocationResult
from app.agents.revenue_validation.schemas import (
    BuyerProfileOutput,
    OpportunityRevenueContext,
    PricingRecommendationOutput,
    RevenueEvidenceOutput,
    RevenueValidationLLMOutput,
)


class MockRevenueValidationLLMClient:
    def __init__(
        self,
        responses: list[RevenueValidationLLMOutput | None] | dict[UUID, RevenueValidationLLMOutput],
        *,
        model: str = "mock-revenue-validation",
    ) -> None:
        if isinstance(responses, dict):
            self._by_opportunity = responses
            self._responses: list[RevenueValidationLLMOutput | None] = []
        else:
            self._by_opportunity = {}
            self._responses = list(responses)
        self._index = 0
        self._model = model
        self.call_count = 0

    async def validate_revenue(
        self,
        *,
        context: OpportunityRevenueContext,
        attempt: int,
    ) -> LLMInvocationResult:
        del attempt
        self.call_count += 1
        response: RevenueValidationLLMOutput | None = None

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
            prompt_tokens=340,
            completion_tokens=210,
            latency_ms=24,
            cost_usd=0.0,
        )


def default_mock_revenue_validation_output(
    *, include_competitor_pricing: bool = True
) -> RevenueValidationLLMOutput:
    evidence = [
        RevenueEvidenceOutput(
            evidence_type="existing_spending",
            excerpt="Complaints reference paying for ShiftApp and spreadsheet workarounds.",
            source_reference="Linked complaint evidence",
            supports_conclusion="willingness_to_pay",
            confidence="medium",
            complaint_index=0,
        ),
        RevenueEvidenceOutput(
            evidence_type="budget_signal",
            excerpt="Ops teams at SMB scale routinely budget for scheduling tools.",
            source_reference="Buyer profile inference from target user",
            supports_conclusion="revenue_confidence",
            confidence="medium",
        ),
        RevenueEvidenceOutput(
            evidence_type="purchase_frequency",
            excerpt="Scheduling tools are reviewed during annual ops software planning.",
            source_reference="Typical SMB software purchase cycle",
            supports_conclusion="frequency",
            confidence="medium",
        ),
    ]
    if include_competitor_pricing:
        evidence.insert(
            0,
            RevenueEvidenceOutput(
                evidence_type="competitor_pricing",
                excerpt="ShiftApp lists per-user monthly pricing starting around $8.",
                source_reference="Competitor pricing context: ShiftApp",
                supports_conclusion="pricing",
                confidence="high",
                competitor_index=0,
            ),
        )

    return RevenueValidationLLMOutput(
        willingness_to_pay_score=74,
        revenue_confidence_score=68,
        pricing_recommendations=[
            PricingRecommendationOutput(
                tier_name="Starter",
                price_usd=29.0,
                billing_period="flat_monthly",
                target_buyer="Single-location ops managers",
                rationale=(
                    "Lightweight scheduling wedge priced below incumbent per-user tools "
                    "for small teams."
                ),
            ),
            PricingRecommendationOutput(
                tier_name="Growth",
                price_usd=8.0,
                billing_period="per_user_monthly",
                target_buyer="Multi-location SMB ops teams",
                rationale=(
                    "Per-user pricing aligns with hourly staff scale and matches "
                    "competitor entry tiers."
                ),
            ),
        ],
        buyer_profiles=[
            BuyerProfileOutput(
                profile_name="Multi-location retail ops",
                budget_availability="medium",
                purchasing_frequency="annual or quarterly software reviews",
                existing_spending_notes=(
                    "Teams already pay for workforce tools and spreadsheets; budget exists "
                    "for point solutions under $500/month."
                ),
            ),
        ],
        supporting_evidence=evidence,
        executive_summary=(
            "Customers show moderate-to-strong willingness to pay for a focused scheduling "
            "tool. Competitor pricing anchors suggest viable entry tiers near $8–29/month, "
            "with reasonable revenue confidence for an SMB ops buyer."
        ),
    )
