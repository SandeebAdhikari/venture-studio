"""LangGraph workflow for go-to-market planning."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.budget_guard import serialize_llm_invocation
from app.agents.go_to_market.llm_client import GoToMarketLLMClient
from app.agents.go_to_market.metrics import compute_ranking_metrics, generate_acquisition_roadmap
from app.agents.go_to_market.schemas import (
    GoToMarketDraft,
    GoToMarketLLMOutput,
    GoToMarketResult,
    LLMInvocationResult,
    OpportunityGTMContext,
)
from app.agents.go_to_market.validator import GoToMarketValidationError, GoToMarketValidator
from app.config import Settings
from app.logging import get_logger

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)

GRAPH_NAME = "plan_go_to_market"


class GTMState(TypedDict):
    context: OpportunityGTMContext
    attempt: int
    max_attempts: int
    llm_output: GoToMarketLLMOutput | None
    draft: GoToMarketDraft | None
    skip_reason: str | None
    error: str | None
    invocations: list[dict[str, Any]]
    validation_errors: list[str]
    status: Literal["pending", "completed", "skipped", "failed"]


class GoToMarketAgent:
    def __init__(
        self,
        llm_client: GoToMarketLLMClient,
        settings: Settings,
        validator: GoToMarketValidator | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._llm = llm_client
        self._settings = settings
        self._validator = validator or GoToMarketValidator()
        self._budget = budget_service
        self._graph = self._build_graph()

    async def run(self, context: OpportunityGTMContext) -> GoToMarketResult:
        initial_state: GTMState = {
            "context": context,
            "attempt": 1,
            "max_attempts": self._settings.go_to_market_max_retries,
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
        graph = StateGraph(GTMState)
        graph.add_node("gather_context", self._gather_context)
        graph.add_node("plan_gtm", self._plan_gtm)
        graph.add_node("check", self._check)
        graph.add_node("finalize", self._finalize)

        graph.set_entry_point("gather_context")
        graph.add_edge("gather_context", "plan_gtm")
        graph.add_edge("plan_gtm", "check")
        graph.add_conditional_edges(
            "check",
            self._route_after_check,
            {"retry": "plan_gtm", "finalize": "finalize", "fail": "finalize"},
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    async def _gather_context(self, state: GTMState) -> dict[str, Any]:
        if not state["context"].title.strip():
            return {"status": "failed", "error": "missing_opportunity_title"}
        return {}

    async def _plan_gtm(self, state: GTMState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        model = self._settings.go_to_market_model
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

        invocation = await self._llm.plan_gtm(
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

    async def _check(self, state: GTMState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        llm_output = state.get("llm_output")
        if llm_output is None:
            return {}

        try:
            validated = self._validator.validate(llm_output, context=state["context"])
        except GoToMarketValidationError as exc:
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

        acquisition_roadmap = generate_acquisition_roadmap(validated.acquisition_phases)
        ranking_metrics = compute_ranking_metrics(
            validated,
            acquisition_roadmap=acquisition_roadmap,
        )
        draft = GoToMarketDraft(
            ideal_customer_profile=validated.ideal_customer_profile,
            customer_personas=validated.customer_personas,
            acquisition_channels=validated.acquisition_channels,
            outreach_strategy=validated.outreach_strategy,
            content_strategy=validated.content_strategy,
            seo_opportunities=validated.seo_opportunities,
            partnerships=validated.partnerships,
            first_100_customers_plan=validated.first_100_customers_plan,
            acquisition_roadmap=acquisition_roadmap,
            estimated_cac_usd=validated.estimated_cac_usd,
            confidence_score=validated.confidence_score,
            gtm_report=validated.gtm_report,
            supporting_evidence=validated.supporting_evidence,
            ranking_metrics=ranking_metrics,
        )
        return {"draft": draft, "status": "completed"}

    async def _finalize(self, state: GTMState) -> dict[str, Any]:
        logger.info(
            "Go-to-market planning finished",
            extra={
                "opportunity_id": str(state["context"].opportunity_id),
                "status": state.get("status"),
                "attempts": state.get("attempt"),
            },
        )
        return {}

    def _route_after_check(self, state: GTMState) -> str:
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

    def _to_result(self, state: GTMState) -> GoToMarketResult:
        status = state.get("status", "failed")
        if status == "pending":
            status = "failed"

        return GoToMarketResult(
            opportunity_id=state["context"].opportunity_id,
            status=status,  # type: ignore[arg-type]
            draft=state.get("draft"),
            skip_reason=state.get("skip_reason"),
            error=state.get("error"),
            attempts=state.get("attempt", 0),
            eval_logs=state.get("invocations", []),
        )
