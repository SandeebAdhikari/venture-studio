"""LangGraph workflow for market intelligence research."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.budget_guard import serialize_llm_invocation
from app.agents.market_research.llm_client import MarketResearchLLMClient
from app.agents.market_research.schemas import (
    LLMInvocationResult,
    MarketResearchDraft,
    MarketResearchLLMOutput,
    MarketResearchResult,
    OpportunityResearchContext,
)
from app.agents.market_research.validator import (
    MarketResearchValidationError,
    MarketResearchValidator,
)
from app.config import Settings
from app.logging import get_logger

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)

GRAPH_NAME = "research_market"


class ResearchState(TypedDict):
    context: OpportunityResearchContext
    attempt: int
    max_attempts: int
    llm_output: MarketResearchLLMOutput | None
    draft: MarketResearchDraft | None
    skip_reason: str | None
    error: str | None
    invocations: list[dict[str, Any]]
    validation_errors: list[str]
    status: Literal["pending", "completed", "skipped", "failed"]


class MarketResearchAgent:
    """Runs research_market LangGraph for one opportunity."""

    def __init__(
        self,
        llm_client: MarketResearchLLMClient,
        settings: Settings,
        validator: MarketResearchValidator | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._llm = llm_client
        self._settings = settings
        self._validator = validator or MarketResearchValidator()
        self._budget = budget_service
        self._graph = self._build_graph()

    async def run(self, context: OpportunityResearchContext) -> MarketResearchResult:
        initial_state: ResearchState = {
            "context": context,
            "attempt": 1,
            "max_attempts": self._settings.research_max_retries,
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
        graph = StateGraph(ResearchState)
        graph.add_node("gather_context", self._gather_context)
        graph.add_node("research", self._research)
        graph.add_node("validate", self._validate)
        graph.add_node("finalize", self._finalize)

        graph.set_entry_point("gather_context")
        graph.add_edge("gather_context", "research")
        graph.add_edge("research", "validate")
        graph.add_conditional_edges(
            "validate",
            self._route_after_validate,
            {
                "retry": "research",
                "finalize": "finalize",
                "fail": "finalize",
            },
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    async def _gather_context(self, state: ResearchState) -> dict[str, Any]:
        if not state["context"].title.strip():
            return {
                "status": "failed",
                "error": "missing_opportunity_title",
            }
        return {}

    async def _research(self, state: ResearchState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        model = self._settings.research_model
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

        prior_errors = state.get("validation_errors") or []
        invocation = await self._llm.research(
            context=state["context"],
            attempt=state["attempt"],
            validation_errors=prior_errors if prior_errors else None,
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

        return {
            "invocations": invocations,
            "llm_output": invocation.parsed,
        }

    async def _validate(self, state: ResearchState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        llm_output = state.get("llm_output")
        if llm_output is None:
            return {}

        try:
            validated = self._validator.validate(llm_output)
        except MarketResearchValidationError as exc:
            errors = list(state.get("validation_errors", []))
            errors.extend(exc.errors)
            invocations = list(state["invocations"])
            if invocations:
                last = dict(invocations[-1])
                last["validation_errors"] = list(exc.errors)
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

        draft = MarketResearchDraft(
            market_size_usd=validated.market_size_usd,
            tam_usd=validated.tam_usd,
            sam_usd=validated.sam_usd,
            industry_growth_rate_pct=validated.industry_growth_rate_pct,
            customer_segments=validated.customer_segments,
            industry_trends=validated.industry_trends,
            supporting_evidence=validated.supporting_evidence,
            executive_summary=validated.executive_summary,
        )
        return {
            "draft": draft,
            "status": "completed",
        }

    async def _finalize(self, state: ResearchState) -> dict[str, Any]:
        logger.info(
            "Market research finished",
            extra={
                "opportunity_id": str(state["context"].opportunity_id),
                "status": state.get("status"),
                "attempts": state.get("attempt"),
            },
        )
        return {}

    def _route_after_validate(self, state: ResearchState) -> str:
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

    def _to_result(self, state: ResearchState) -> MarketResearchResult:
        status = state.get("status", "failed")
        if status == "pending":
            status = "failed"

        return MarketResearchResult(
            opportunity_id=state["context"].opportunity_id,
            status=status,  # type: ignore[arg-type]
            draft=state.get("draft"),
            skip_reason=state.get("skip_reason"),
            error=state.get("error"),
            attempts=state.get("attempt", 0),
            validation_errors=state.get("validation_errors", []),
            eval_logs=state.get("invocations", []),
        )
