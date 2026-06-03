"""Mock LLM client for human proxy tests."""

from __future__ import annotations

from uuid import UUID

from app.agents.human_proxy.llm_client import LLMInvocationResult
from app.agents.human_proxy.schemas import (
    CapitalRequirementsOutput,
    ExecutionComplexityOutput,
    FounderFitAnalysisOutput,
    HumanProxyLLMOutput,
    ImplementationFeasibilityOutput,
    LearningCurveOutput,
    OpportunityProxyContext,
    ProxyEvidenceOutput,
)


class MockHumanProxyLLMClient:
    def __init__(
        self,
        responses: list[HumanProxyLLMOutput | None] | dict[UUID, HumanProxyLLMOutput],
        *,
        model: str = "mock-human-proxy",
    ) -> None:
        if isinstance(responses, dict):
            self._by_opportunity = responses
            self._responses: list[HumanProxyLLMOutput | None] = []
        else:
            self._by_opportunity = {}
            self._responses = list(responses)
        self._index = 0
        self._model = model
        self.call_count = 0

    async def evaluate_founder_fit(
        self,
        *,
        context: OpportunityProxyContext,
        attempt: int,
    ) -> LLMInvocationResult:
        del attempt
        self.call_count += 1
        response: HumanProxyLLMOutput | None = None

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
            prompt_tokens=360,
            completion_tokens=240,
            latency_ms=26,
            cost_usd=0.0,
        )


def default_mock_human_proxy_output() -> HumanProxyLLMOutput:
    return HumanProxyLLMOutput(
        founder_fit_score=82,
        feasibility_score=76,
        recommendation="pursue",
        founder_fit_analysis=FounderFitAnalysisOutput(
            score=82,
            skill_matches=["Next.js", "TypeScript", "Python", "PostgreSQL"],
            skill_gaps=["Mobile native apps"],
            rationale=(
                "A B2B scheduling SaaS maps cleanly to the founder's full-stack web and "
                "PostgreSQL skills with no major stack pivot required."
            ),
        ),
        implementation_feasibility=ImplementationFeasibilityOutput(
            score=76,
            build_complexity="medium",
            rationale=(
                "Core workflows are achievable as a solo-built web app with standard CRUD, "
                "notifications, and role-based access."
            ),
            blockers=["Real-time notification reliability"],
        ),
        learning_curve=LearningCurveOutput(
            score=35,
            difficulty="low",
            new_skills_required=["Workforce compliance nuances"],
            rationale=(
                "Most implementation work uses familiar frameworks; domain learning is moderate."
            ),
        ),
        execution_complexity=ExecutionComplexityOutput(
            score=48,
            complexity_level="medium",
            operational_burden="Moderate ongoing support for multi-location scheduling edge cases",
            rationale=(
                "Solo founder can ship MVP, but customer onboarding and support "
                "add operational load."
            ),
        ),
        capital_requirements=CapitalRequirementsOutput(
            score=72,
            estimated_monthly_usd="$100-$400",
            bootstrap_friendly=True,
            rationale=(
                "Can launch on managed Postgres, basic hosting, and email tooling within a "
                "limited budget."
            ),
        ),
        supporting_evidence=[
            ProxyEvidenceOutput(
                evidence_type="skill_signal",
                excerpt="Opportunity is a B2B SaaS workflow tool suitable for a web stack.",
                source_reference="Opportunity problem and gap statements",
                supports_conclusion="founder_fit",
                confidence="high",
            ),
            ProxyEvidenceOutput(
                evidence_type="complexity_signal",
                excerpt="Scheduling coordination pain is workflow-focused rather than deep ML.",
                source_reference="Linked complaint evidence",
                supports_conclusion="feasibility",
                confidence="medium",
                complaint_index=0,
            ),
            ProxyEvidenceOutput(
                evidence_type="constraint_signal",
                excerpt="Solo founder with limited budget and time needs a focused MVP wedge.",
                source_reference="Founder profile constraints",
                supports_conclusion="recommendation",
                confidence="high",
            ),
        ],
        executive_summary=(
            "This opportunity is a strong fit for a solo technical founder with Next.js, "
            "TypeScript, Python, and PostgreSQL skills. The MVP is feasible within limited "
            "budget and time, with moderate execution complexity and bootstrap-friendly "
            "capital needs. Recommendation: pursue."
        ),
    )
