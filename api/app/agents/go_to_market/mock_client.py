"""Mock LLM client for go-to-market tests."""

from __future__ import annotations

from uuid import UUID

from app.agents.go_to_market.llm_client import LLMInvocationResult
from app.agents.go_to_market.schemas import (
    AcquisitionChannelOutput,
    AcquisitionPhaseOutput,
    ContentStrategyOutput,
    CustomerPersonaOutput,
    First100CustomersPlanOutput,
    GoToMarketLLMOutput,
    GTMEvidenceOutput,
    IdealCustomerProfileOutput,
    OpportunityGTMContext,
    OutreachStrategyOutput,
    PartnershipOutput,
    SEOOpportunityOutput,
)


class MockGoToMarketLLMClient:
    def __init__(
        self,
        responses: list[GoToMarketLLMOutput | None] | dict[UUID, GoToMarketLLMOutput],
        *,
        model: str = "mock-go-to-market",
    ) -> None:
        if isinstance(responses, dict):
            self._by_opportunity = responses
            self._responses: list[GoToMarketLLMOutput | None] = []
        else:
            self._by_opportunity = {}
            self._responses = list(responses)
        self._index = 0
        self._model = model
        self.call_count = 0

    async def plan_gtm(
        self,
        *,
        context: OpportunityGTMContext,
        attempt: int,
    ) -> LLMInvocationResult:
        del attempt
        self.call_count += 1
        response: GoToMarketLLMOutput | None = None

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
            prompt_tokens=420,
            completion_tokens=310,
            latency_ms=32,
            cost_usd=0.0,
        )


def default_mock_go_to_market_output() -> GoToMarketLLMOutput:
    return GoToMarketLLMOutput(
        ideal_customer_profile=IdealCustomerProfileOutput(
            summary=(
                "Multi-location SMB ops leaders managing hourly staff who currently "
                "coordinate schedules with spreadsheets and legacy tools."
            ),
            company_size="20-200 employees",
            industry="Retail, hospitality, and field services",
            geography="United States and Canada",
            budget_range="$200-$800/month for ops software",
            buying_triggers=[
                "Repeated shift swap chaos",
                "Manager time lost to manual scheduling",
                "Need for multi-location visibility",
            ],
        ),
        customer_personas=[
            CustomerPersonaOutput(
                persona_name="Ops admin at multi-location retail",
                role="Operations manager",
                goals=["Reduce scheduling errors", "Approve shift swaps quickly"],
                pain_points=["Last-minute shift changes", "Spreadsheet coordination"],
                preferred_channels=["LinkedIn", "Ops communities", "Referrals"],
            ),
            CustomerPersonaOutput(
                persona_name="Franchise owner",
                role="Business owner",
                goals=["Standardize scheduling across locations", "Control labor costs"],
                pain_points=["No visibility into staffing gaps", "Heavy incumbent tools"],
                preferred_channels=["Industry associations", "Local business groups"],
            ),
        ],
        acquisition_channels=[
            AcquisitionChannelOutput(
                channel_name="Ops admin communities",
                channel_type="community",
                rationale="Target users already discuss scheduling pain in ops forums.",
                priority="primary",
                estimated_cac_usd=120.0,
            ),
            AcquisitionChannelOutput(
                channel_name="Comparison SEO content",
                channel_type="content",
                rationale="Buyers search for lightweight alternatives to incumbent tools.",
                priority="primary",
                estimated_cac_usd=85.0,
            ),
            AcquisitionChannelOutput(
                channel_name="Workforce software partners",
                channel_type="partnership",
                rationale="Integrations with payroll or POS vendors create warm introductions.",
                priority="secondary",
                estimated_cac_usd=160.0,
            ),
        ],
        outreach_strategy=OutreachStrategyOutput(
            primary_motion="Founder-led outbound to ops admins with scheduling pain",
            messaging_themes=[
                "Stop shift swap chaos",
                "Replace spreadsheet scheduling",
                "Launch in one location first",
            ],
            cadence="Two-touch email plus community follow-up over 10 days",
            conversion_tactics=[
                "Offer pilot for one location",
                "Share before/after scheduling workflow",
                "Invite to live swap-approval demo",
            ],
        ),
        content_strategy=ContentStrategyOutput(
            themes=[
                "Hourly staff scheduling workflows",
                "Shift swap best practices",
                "Ops admin productivity",
            ],
            formats=["Comparison guides", "Short demo videos", "Workflow templates"],
            distribution_plan=(
                "Publish on site, syndicate in ops communities, repurpose for outbound"
            ),
            publishing_cadence="Two assets per week during launch phase",
        ),
        seo_opportunities=[
            SEOOpportunityOutput(
                keyword_theme="staff scheduling software for small business",
                search_intent="commercial investigation",
                content_angle="Lightweight alternative to heavy workforce suites",
                priority="high",
            ),
            SEOOpportunityOutput(
                keyword_theme="shift swap approval workflow",
                search_intent="problem-aware",
                content_angle="How ops teams stop last-minute scheduling chaos",
                priority="medium",
            ),
        ],
        partnerships=[
            PartnershipOutput(
                partner_type="Payroll providers",
                partner_examples=["Gusto partners", "Local payroll consultants"],
                value_exchange="Referral fee or bundled onboarding for shared SMB customers",
                priority="high",
            ),
            PartnershipOutput(
                partner_type="Retail POS vendors",
                partner_examples=["Square ecosystem partners"],
                value_exchange="Integration marketplace listing and co-marketing",
                priority="medium",
            ),
        ],
        first_100_customers_plan=First100CustomersPlanOutput(
            target_segments=[
                "Multi-location retail ops admins",
                "Service businesses with hourly staff",
            ],
            acquisition_tactics=[
                "Founder outbound to ops admins discussing scheduling pain",
                "Publish comparison content and capture inbound demos",
                "Run 3-location pilot offer in ops communities",
            ],
            weekly_targets=[
                "Weeks 1-4: 10 discovery calls per week",
                "Weeks 5-8: 5 pilot starts per week",
                "Weeks 9-12: 8 paid conversions per week",
            ],
            success_metrics=[
                "Pilot-to-paid conversion rate",
                "Time to first approved shift swap",
                "CAC payback under 6 months",
            ],
        ),
        acquisition_phases=[
            AcquisitionPhaseOutput(
                phase_name="Founder-led discovery",
                duration_weeks=4,
                focus="Validate ICP and messaging with direct outreach",
                channels=["Outbound email", "Ops communities"],
                targets=["40 qualified conversations", "10 pilot prospects"],
                milestones=["Messaging tested", "First 5 pilots identified"],
            ),
            AcquisitionPhaseOutput(
                phase_name="Content-led inbound",
                duration_weeks=6,
                focus="Capture demand with SEO and comparison content",
                channels=["SEO content", "Community distribution"],
                targets=["2,000 monthly site visits", "25 inbound demos"],
                milestones=["Top comparison page live", "Inbound demo flow working"],
            ),
            AcquisitionPhaseOutput(
                phase_name="Partnership acceleration",
                duration_weeks=6,
                focus="Scale acquisition through payroll and POS partners",
                channels=["Partnerships", "Referrals"],
                targets=["3 active partner channels", "30 referred leads"],
                milestones=["First partner referral loop live"],
            ),
        ],
        estimated_cac_usd=135.0,
        confidence_score=72,
        gtm_report=(
            "The strongest initial wedge is founder-led acquisition into multi-location SMB "
            "ops teams experiencing shift swap chaos. Community presence and comparison SEO "
            "should build inbound demand while payroll partnerships create scalable referrals. "
            "A phased 16-week roadmap can reach the first 100 customers with an estimated CAC "
            "near $135 if pilots convert through a focused swap-approval workflow demo."
        ),
        supporting_evidence=[
            GTMEvidenceOutput(
                evidence_type="pain_point",
                excerpt="Employees swap shifts without notice, breaking weekly schedules.",
                source_reference="Linked complaint evidence",
                supports_conclusion="icp",
                confidence="high",
                complaint_index=0,
            ),
            GTMEvidenceOutput(
                evidence_type="audience_signal",
                excerpt=(
                    "Ops admins at multi-location service businesses are the stated target user."
                ),
                source_reference="Opportunity target user",
                supports_conclusion="persona",
                confidence="medium",
            ),
            GTMEvidenceOutput(
                evidence_type="channel_signal",
                excerpt=(
                    "Teams discuss scheduling pain in ops communities "
                    "and compare incumbent tools."
                ),
                source_reference="Opportunity alternatives and frequency signal",
                supports_conclusion="channel",
                confidence="medium",
            ),
        ],
    )
