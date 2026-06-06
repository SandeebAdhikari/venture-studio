"""LangGraph workflow for product strategy planning."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.budget_guard import serialize_llm_invocation
from app.agents.product_strategy.llm_client import ProductStrategyLLMClient
from app.agents.product_strategy.metrics import compute_planning_metrics, generate_roadmap
from app.agents.product_strategy.schemas import (
    LLMInvocationResult,
    OpportunityPlanningContext,
    ProductStrategyDraft,
    ProductStrategyLLMOutput,
    ProductStrategyResult,
)
from app.agents.product_strategy.validator import (
    ProductStrategyValidationError,
    ProductStrategyValidator,
)
from app.config import Settings
from app.logging import get_logger

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)

GRAPH_NAME = "plan_product_strategy"


class PlanningState(TypedDict):
    context: OpportunityPlanningContext
    attempt: int
    max_attempts: int
    llm_output: ProductStrategyLLMOutput | None
    draft: ProductStrategyDraft | None
    skip_reason: str | None
    error: str | None
    invocations: list[dict[str, Any]]
    validation_errors: list[str]
    status: Literal["pending", "completed", "skipped", "failed"]


class ProductStrategyAgent:
    def __init__(
        self,
        llm_client: ProductStrategyLLMClient,
        settings: Settings,
        validator: ProductStrategyValidator | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._llm = llm_client
        self._settings = settings
        self._validator = validator or ProductStrategyValidator()
        self._budget = budget_service
        self._graph = self._build_graph()

    async def run(self, context: OpportunityPlanningContext) -> ProductStrategyResult:
        initial_state: PlanningState = {
            "context": context,
            "attempt": 1,
            "max_attempts": self._settings.product_strategy_max_retries,
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
        graph = StateGraph(PlanningState)
        graph.add_node("gather_context", self._gather_context)
        graph.add_node("plan_product", self._plan_product)
        graph.add_node("check", self._check)
        graph.add_node("finalize", self._finalize)

        graph.set_entry_point("gather_context")
        graph.add_edge("gather_context", "plan_product")
        graph.add_edge("plan_product", "check")
        graph.add_conditional_edges(
            "check",
            self._route_after_check,
            {"retry": "plan_product", "finalize": "finalize", "fail": "finalize"},
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    async def _gather_context(self, state: PlanningState) -> dict[str, Any]:
        if not state["context"].title.strip():
            return {"status": "failed", "error": "missing_opportunity_title"}
        return {}

    async def _plan_product(self, state: PlanningState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        model = self._settings.product_strategy_model
        estimated_cost = 0.0
        if self._budget is not None:
            estimated_cost, block_reason = await self._budget.try_prepare_call(GRAPH_NAME, model)
            if block_reason:
                invocation = LLMInvocationResult(model=model, error=block_reason)
                invocations = list(state["invocations"])
                invocations.append(
                    serialize_llm_invocation(
                        state["attempt"],
                        invocation,
                        estimated_cost_usd=estimated_cost,
                    )
                )
                if state["attempt"] >= state["max_attempts"]:
                    return {
                        "invocations": invocations,
                        "error": block_reason,
                        "status": "failed",
                    }
                return {
                    "invocations": invocations,
                    "attempt": state["attempt"] + 1,
                    "validation_errors": [block_reason],
                    "llm_output": None,
                }

        invocation = await self._llm.plan_product(
            context=state["context"],
            attempt=state["attempt"],
        )
        invocations = list(state["invocations"])
        invocations.append(
            serialize_llm_invocation(
                state["attempt"],
                invocation,
                estimated_cost_usd=estimated_cost,
            )
        )

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

    async def _check(self, state: PlanningState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        llm_output = state.get("llm_output")
        if llm_output is None:
            return {}

        try:
            validated = self._validator.validate(llm_output, context=state["context"])
        except ProductStrategyValidationError as exc:
            errors = list(state.get("validation_errors", []))
            errors.extend(exc.errors)
            invocations = list(state["invocations"])
            if invocations:
                last = dict(invocations[-1])
                last["validation_errors"] = list(exc.errors)
                last["error"] = "; ".join(exc.errors)
                invocations[-1] = last
            if state["attempt"] >= state["max_attempts"]:
                return {
                    "invocations": invocations,
                    "validation_errors": errors,
                    "error": "; ".join(exc.errors),
                    "status": "failed",
                }
            return {
                "invocations": invocations,
                "validation_errors": errors,
                "attempt": state["attempt"] + 1,
                "llm_output": None,
            }

        roadmap = generate_roadmap(validated.development_phases, validated.estimated_timeline)
        metrics = compute_planning_metrics(validated, roadmap=roadmap)
        draft = ProductStrategyDraft(
            mvp_definition=validated.mvp_definition,
            core_features=validated.core_features,
            feature_priorities=validated.feature_priorities,
            development_phases=validated.development_phases,
            estimated_timeline=validated.estimated_timeline,
            technical_risks=validated.technical_risks,
            roadmap=roadmap,
            supporting_evidence=validated.supporting_evidence,
            executive_summary=validated.executive_summary,
            planning_metrics=metrics,
        )
        return {"draft": draft, "status": "completed"}

    async def _finalize(self, state: PlanningState) -> dict[str, Any]:
        logger.info(
            "Product strategy planning finished",
            extra={
                "opportunity_id": str(state["context"].opportunity_id),
                "status": state.get("status"),
                "attempts": state.get("attempt"),
            },
        )
        return {}

    def _route_after_check(self, state: PlanningState) -> str:
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

    def _to_result(self, state: PlanningState) -> ProductStrategyResult:
        status = state.get("status", "failed")
        if status == "pending":
            status = "failed"

        return ProductStrategyResult(
            opportunity_id=state["context"].opportunity_id,
            status=status,  # type: ignore[arg-type]
            draft=state.get("draft"),
            skip_reason=state.get("skip_reason"),
            error=state.get("error"),
            attempts=state.get("attempt", 0),
            eval_logs=state.get("invocations", []),
        )
