"""LangGraph workflow for growth strategy evaluation."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.growth_strategy.llm_client import GrowthStrategyLLMClient
from app.agents.growth_strategy.metrics import compute_evaluation_metrics, generate_growth_roadmap
from app.agents.growth_strategy.schemas import (
    GrowthStrategyDraft,
    GrowthStrategyLLMOutput,
    GrowthStrategyResult,
    LLMInvocationResult,
    OpportunityGrowthContext,
)
from app.agents.growth_strategy.validator import (
    GrowthStrategyValidationError,
    GrowthStrategyValidator,
)
from app.config import Settings
from app.logging import get_logger

logger = get_logger(__name__)

GRAPH_NAME = "evaluate_growth_strategy"


class GrowthState(TypedDict):
    context: OpportunityGrowthContext
    attempt: int
    max_attempts: int
    llm_output: GrowthStrategyLLMOutput | None
    draft: GrowthStrategyDraft | None
    skip_reason: str | None
    error: str | None
    invocations: list[dict[str, Any]]
    validation_errors: list[str]
    status: Literal["pending", "completed", "skipped", "failed"]


class GrowthStrategyAgent:
    def __init__(
        self,
        llm_client: GrowthStrategyLLMClient,
        settings: Settings,
        validator: GrowthStrategyValidator | None = None,
    ) -> None:
        self._llm = llm_client
        self._settings = settings
        self._validator = validator or GrowthStrategyValidator()
        self._graph = self._build_graph()

    async def run(self, context: OpportunityGrowthContext) -> GrowthStrategyResult:
        initial_state: GrowthState = {
            "context": context,
            "attempt": 1,
            "max_attempts": self._settings.growth_strategy_max_retries,
            "llm_output": None,
            "draft": None,
            "skip_reason": None,
            "error": None,
            "invocations": [],
            "validation_errors": [],
            "status": "pending",
        }
        final_state = await self._graph.ainvoke(initial_state)
        return self._to_result(final_state)

    def _build_graph(self):
        graph = StateGraph(GrowthState)
        graph.add_node("gather_context", self._gather_context)
        graph.add_node("evaluate_growth", self._evaluate_growth)
        graph.add_node("check", self._check)
        graph.add_node("finalize", self._finalize)

        graph.set_entry_point("gather_context")
        graph.add_edge("gather_context", "evaluate_growth")
        graph.add_edge("evaluate_growth", "check")
        graph.add_conditional_edges(
            "check",
            self._route_after_check,
            {"retry": "evaluate_growth", "finalize": "finalize", "fail": "finalize"},
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    async def _gather_context(self, state: GrowthState) -> dict[str, Any]:
        if not state["context"].title.strip():
            return {"status": "failed", "error": "missing_opportunity_title"}
        return {}

    async def _evaluate_growth(self, state: GrowthState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        invocation = await self._llm.evaluate_growth(
            context=state["context"],
            attempt=state["attempt"],
        )
        invocations = list(state["invocations"])
        invocations.append(self._serialize_invocation(state["attempt"], invocation))

        if invocation.error or invocation.parsed is None:
            if state["attempt"] >= state["max_attempts"]:
                return {
                    "invocations": invocations,
                    "error": invocation.error or "malformed_response",
                    "status": "failed",
                }
            return {
                "invocations": invocations,
                "attempt": state["attempt"] + 1,
                "validation_errors": [invocation.error or "malformed_response"],
                "llm_output": None,
            }

        return {"invocations": invocations, "llm_output": invocation.parsed}

    async def _check(self, state: GrowthState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        llm_output = state.get("llm_output")
        if llm_output is None:
            return {}

        try:
            validated = self._validator.validate(llm_output, context=state["context"])
        except GrowthStrategyValidationError as exc:
            errors = list(state.get("validation_errors", []))
            errors.extend(exc.errors)
            if state["attempt"] >= state["max_attempts"]:
                return {
                    "validation_errors": errors,
                    "error": "; ".join(exc.errors),
                    "status": "failed",
                }
            return {
                "validation_errors": errors,
                "attempt": state["attempt"] + 1,
                "llm_output": None,
            }

        growth_roadmap = generate_growth_roadmap(validated.growth_phases)
        metrics = compute_evaluation_metrics(validated, growth_roadmap=growth_roadmap)
        draft = GrowthStrategyDraft(
            growth_score=validated.growth_score,
            scalability_score=validated.scalability_score,
            risk_score=validated.risk_score,
            seo_potential=validated.seo_potential,
            referral_potential=validated.referral_potential,
            partnership_opportunities=validated.partnership_opportunities,
            paid_acquisition_potential=validated.paid_acquisition_potential,
            market_expansion_opportunities=validated.market_expansion_opportunities,
            growth_roadmap=growth_roadmap,
            supporting_evidence=validated.supporting_evidence,
            executive_summary=validated.executive_summary,
            evaluation_metrics=metrics,
        )
        return {"draft": draft, "status": "completed"}

    async def _finalize(self, state: GrowthState) -> dict[str, Any]:
        logger.info(
            "Growth strategy evaluation finished",
            extra={
                "opportunity_id": str(state["context"].opportunity_id),
                "status": state.get("status"),
                "attempts": state.get("attempt"),
            },
        )
        return {}

    def _route_after_check(self, state: GrowthState) -> str:
        if state.get("status") == "failed":
            return "fail"
        if state.get("status") == "skipped":
            return "finalize"
        if state.get("draft") is not None:
            return "finalize"
        if state.get("llm_output") is None and state["attempt"] <= state["max_attempts"]:
            return "retry"
        if state.get("validation_errors") and state["attempt"] <= state["max_attempts"]:
            return "retry"
        return "fail"

    def _to_result(self, state: GrowthState) -> GrowthStrategyResult:
        status = state.get("status", "failed")
        if status == "pending":
            status = "failed"

        return GrowthStrategyResult(
            opportunity_id=state["context"].opportunity_id,
            status=status,  # type: ignore[arg-type]
            draft=state.get("draft"),
            skip_reason=state.get("skip_reason"),
            error=state.get("error"),
            attempts=state.get("attempt", 0),
            eval_logs=state.get("invocations", []),
        )

    @staticmethod
    def _serialize_invocation(attempt: int, invocation: LLMInvocationResult) -> dict[str, Any]:
        return {
            "attempt": attempt,
            "model": invocation.model,
            "prompt_tokens": invocation.prompt_tokens,
            "completion_tokens": invocation.completion_tokens,
            "latency_ms": invocation.latency_ms,
            "cost_usd": invocation.cost_usd,
            "error": invocation.error,
            "parsed": invocation.parsed.model_dump() if invocation.parsed else None,
            "raw_text": invocation.raw_text,
        }
