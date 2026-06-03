"""Mock LLM client for growth strategy tests."""

from __future__ import annotations

from uuid import UUID

from app.agents.growth_strategy.llm_client import LLMInvocationResult
from app.agents.growth_strategy.schemas import (
    GrowthEvidenceOutput,
    GrowthPhaseOutput,
    GrowthStrategyLLMOutput,
    MarketExpansionOutput,
    OpportunityGrowthContext,
    PaidAcquisitionPotentialOutput,
    PartnershipOpportunityOutput,
    ReferralPotentialOutput,
    SEOPotentialOutput,
)


class MockGrowthStrategyLLMClient:
    def __init__(
        self,
        responses: list[GrowthStrategyLLMOutput | None] | dict[UUID, GrowthStrategyLLMOutput],
        *,
        model: str = "mock-growth-strategy",
    ) -> None:
        if isinstance(responses, dict):
            self._by_opportunity = responses
            self._responses: list[GrowthStrategyLLMOutput | None] = []
        else:
            self._by_opportunity = {}
            self._responses = list(responses)
        self._index = 0
        self._model = model
        self.call_count = 0

    async def evaluate_growth(
        self,
        *,
        context: OpportunityGrowthContext,
        attempt: int,
    ) -> LLMInvocationResult:
        del attempt
        self.call_count += 1
        response: GrowthStrategyLLMOutput | None = None

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
            prompt_tokens=400,
            completion_tokens=280,
            latency_ms=30,
            cost_usd=0.0,
        )


def default_mock_growth_strategy_output() -> GrowthStrategyLLMOutput:
    return GrowthStrategyLLMOutput(
        growth_score=78,
        scalability_score=71,
        risk_score=42,
        seo_potential=SEOPotentialOutput(
            score=74,
            keyword_themes=[
                "staff scheduling software",
                "shift swap workflow",
                "hourly employee scheduling",
            ],
            content_momentum="Steady commercial-intent search around scheduling pain points",
            rationale=(
                "Repeated complaint themes map to searchable workflow problems with "
                "comparison-driven buyer intent."
            ),
        ),
        referral_potential=ReferralPotentialOutput(
            score=66,
            referral_triggers=[
                "Ops admins share scheduling templates",
                "Multi-location managers compare tools in peer groups",
            ],
            viral_loops=[
                "Invite managers during shift swap approvals",
                "Shareable weekly schedule templates",
            ],
            rationale=(
                "Scheduling pain is discussed frequently among ops peers, creating natural "
                "word-of-mouth opportunities."
            ),
        ),
        partnership_opportunities=[
            PartnershipOpportunityOutput(
                partner_type="Payroll providers",
                expansion_lever="Bundled workforce management referrals",
                rationale="SMB payroll vendors already serve the target buyer.",
                priority="high",
            ),
            PartnershipOpportunityOutput(
                partner_type="Retail POS ecosystems",
                expansion_lever="Marketplace integrations for hourly workforce tools",
                rationale="POS vendors reach multi-location operators with scheduling needs.",
                priority="medium",
            ),
        ],
        paid_acquisition_potential=PaidAcquisitionPotentialOutput(
            score=63,
            viable_channels=["LinkedIn ads", "Comparison landing pages", "Retargeting"],
            estimated_cac_range_usd="$90-$160",
            rationale=(
                "Defined ICP and workflow-specific keywords support efficient paid tests "
                "after initial SEO content exists."
            ),
        ),
        market_expansion_opportunities=[
            MarketExpansionOutput(
                segment_name="Healthcare clinic scheduling",
                geography="United States",
                expansion_rationale=(
                    "Similar hourly staffing coordination pain with higher compliance needs."
                ),
                priority="medium",
            ),
            MarketExpansionOutput(
                segment_name="Franchise food service",
                geography="North America",
                expansion_rationale="Multi-location hourly workforce matches current ICP patterns.",
                priority="high",
            ),
        ],
        growth_phases=[
            GrowthPhaseOutput(
                phase_name="Organic demand capture",
                duration_months=6,
                focus="Build SEO moat and referral loops in core SMB ops segment",
                growth_levers=["Comparison content", "Community distribution", "Template sharing"],
                milestones=["Top 3 ranking for core keyword cluster", "Referral loop live"],
            ),
            GrowthPhaseOutput(
                phase_name="Partnership scale",
                duration_months=9,
                focus="Expand through payroll and POS partner channels",
                growth_levers=["Partner integrations", "Co-marketing", "Referral incentives"],
                milestones=["Two active partner channels", "Partner-sourced pipeline > 20%"],
            ),
            GrowthPhaseOutput(
                phase_name="Adjacent market expansion",
                duration_months=12,
                focus="Enter adjacent hourly workforce verticals",
                growth_levers=["Vertical landing pages", "Industry-specific workflows"],
                milestones=["Launch in two adjacent segments", "Segment-specific retention stable"],
            ),
        ],
        supporting_evidence=[
            GrowthEvidenceOutput(
                evidence_type="demand_signal",
                excerpt="Employees swap shifts without notice, breaking weekly schedules.",
                source_reference="Linked complaint evidence",
                supports_conclusion="seo",
                confidence="high",
                complaint_index=0,
            ),
            GrowthEvidenceOutput(
                evidence_type="market_signal",
                excerpt="Ops admins at multi-location service businesses are the target user.",
                source_reference="Opportunity target user",
                supports_conclusion="expansion",
                confidence="medium",
            ),
            GrowthEvidenceOutput(
                evidence_type="channel_signal",
                excerpt="Teams compare incumbent scheduling tools and discuss alternatives.",
                source_reference="Opportunity alternatives and frequency signal",
                supports_conclusion="paid",
                confidence="medium",
            ),
        ],
        executive_summary=(
            "This opportunity shows strong long-term growth potential through SEO-led demand "
            "capture, peer referral loops, and partnership expansion into payroll and POS "
            "ecosystems. Scalability is solid for an SMB workflow wedge, with moderate risk "
            "from multi-location complexity. A three-phase growth roadmap over 27 months can "
            "expand from core ops scheduling into adjacent hourly workforce segments."
        ),
    )
