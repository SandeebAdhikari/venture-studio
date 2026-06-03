"""Mock LLM client for product strategy tests."""

from __future__ import annotations

from uuid import UUID

from app.agents.product_strategy.llm_client import LLMInvocationResult
from app.agents.product_strategy.schemas import (
    CoreFeatureOutput,
    DevelopmentPhaseOutput,
    EstimatedTimelineOutput,
    FeaturePriorityOutput,
    OpportunityPlanningContext,
    ProductStrategyLLMOutput,
    StrategyEvidenceOutput,
    TechnicalRiskOutput,
)


class MockProductStrategyLLMClient:
    def __init__(
        self,
        responses: list[ProductStrategyLLMOutput | None] | dict[UUID, ProductStrategyLLMOutput],
        *,
        model: str = "mock-product-strategy",
    ) -> None:
        if isinstance(responses, dict):
            self._by_opportunity = responses
            self._responses: list[ProductStrategyLLMOutput | None] = []
        else:
            self._by_opportunity = {}
            self._responses = list(responses)
        self._index = 0
        self._model = model
        self.call_count = 0

    async def plan_product(
        self,
        *,
        context: OpportunityPlanningContext,
        attempt: int,
    ) -> LLMInvocationResult:
        del attempt
        self.call_count += 1
        response: ProductStrategyLLMOutput | None = None

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
            prompt_tokens=380,
            completion_tokens=260,
            latency_ms=28,
            cost_usd=0.0,
        )


def default_mock_product_strategy_output() -> ProductStrategyLLMOutput:
    core_features = [
        CoreFeatureOutput(
            name="Shift swap workflow",
            description="Allow managers to approve or reject last-minute shift swaps in one view.",
            user_value="Reduces scheduling chaos when employees change shifts without notice.",
        ),
        CoreFeatureOutput(
            name="Weekly schedule builder",
            description="Drag-and-drop schedule creation for hourly staff across locations.",
            user_value="Replaces spreadsheet coordination with a shared source of truth.",
        ),
        CoreFeatureOutput(
            name="Coverage alerts",
            description="Notify managers when a shift is understaffed after a swap request.",
            user_value="Prevents missed coverage before shifts start.",
        ),
    ]
    return ProductStrategyLLMOutput(
        mvp_definition=(
            "A lightweight staff scheduling MVP for SMB ops teams that centralizes "
            "shift swaps, weekly schedule creation, and coverage alerts for hourly workers."
        ),
        core_features=core_features,
        feature_priorities=[
            FeaturePriorityOutput(
                feature_name="Shift swap workflow",
                priority="P0",
                rank=1,
                rationale="Directly addresses the highest-frequency scheduling pain in evidence.",
            ),
            FeaturePriorityOutput(
                feature_name="Weekly schedule builder",
                priority="P0",
                rank=2,
                rationale="Core workflow needed to replace spreadsheet-based scheduling.",
            ),
            FeaturePriorityOutput(
                feature_name="Coverage alerts",
                priority="P1",
                rank=3,
                rationale="Important safety net but can follow initial swap workflow launch.",
            ),
        ],
        development_phases=[
            DevelopmentPhaseOutput(
                phase_name="MVP foundation",
                duration_weeks=6,
                deliverables=[
                    "Shift swap request and approval flow",
                    "Basic weekly schedule builder",
                ],
                milestones=[
                    "Internal alpha with one pilot location",
                    "Swap workflow usable end-to-end",
                ],
            ),
            DevelopmentPhaseOutput(
                phase_name="Operational readiness",
                duration_weeks=4,
                deliverables=[
                    "Coverage alerts",
                    "Manager notifications",
                ],
                milestones=[
                    "Beta with 3 pilot customers",
                    "Alerting validated in real shift changes",
                ],
            ),
            DevelopmentPhaseOutput(
                phase_name="Launch hardening",
                duration_weeks=3,
                deliverables=[
                    "Onboarding flow",
                    "Role-based permissions",
                ],
                milestones=[
                    "Production launch checklist complete",
                ],
            ),
        ],
        estimated_timeline=EstimatedTimelineOutput(
            total_weeks=13,
            mvp_weeks=6,
            summary=(
                "Six-week MVP for swap workflow and schedule builder, followed by four weeks "
                "of operational features and three weeks of launch hardening."
            ),
        ),
        technical_risks=[
            TechnicalRiskOutput(
                risk="Real-time notification delivery for shift changes may be unreliable.",
                severity="medium",
                mitigation="Use queued notifications with retry and in-app fallback alerts.",
            ),
            TechnicalRiskOutput(
                risk="Multi-location schedule conflicts increase data model complexity.",
                severity="high",
                mitigation=(
                    "Start with single-location MVP schema and add location scoping in phase 2."
                ),
            ),
        ],
        supporting_evidence=[
            StrategyEvidenceOutput(
                evidence_type="pain_point",
                excerpt="Employees swap shifts without notice, breaking weekly schedules.",
                source_reference="Linked complaint evidence",
                supports_conclusion="mvp",
                confidence="high",
                complaint_index=0,
            ),
            StrategyEvidenceOutput(
                evidence_type="gap",
                excerpt="Teams rely on spreadsheets because existing tools are too heavy.",
                source_reference="Opportunity gap statement",
                supports_conclusion="feature",
                confidence="medium",
            ),
            StrategyEvidenceOutput(
                evidence_type="user_need",
                excerpt="Ops admins need a lightweight workflow for hourly staff scheduling.",
                source_reference="Opportunity target user",
                supports_conclusion="phase",
                confidence="medium",
            ),
        ],
        executive_summary=(
            "The MVP should focus on shift swap approval and a simple weekly schedule builder "
            "for SMB ops teams, with coverage alerts in a second phase. A 13-week roadmap "
            "balances speed to pilot with manageable technical risk."
        ),
    )
