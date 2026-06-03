"""LangGraph workflow for customer demand research."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.customer_research.llm_client import CustomerResearchLLMClient
from app.agents.customer_research.metrics import compute_validation_metrics
from app.agents.customer_research.schemas import (
    CustomerResearchDraft,
    CustomerResearchLLMOutput,
    CustomerResearchResult,
    LLMInvocationResult,
    OpportunityCustomerContext,
)
from app.agents.customer_research.validator import (
    CustomerResearchValidationError,
    CustomerResearchValidator,
)
from app.config import Settings
from app.logging import get_logger

logger = get_logger(__name__)

GRAPH_NAME = "research_customers"


class ResearchState(TypedDict):
    context: OpportunityCustomerContext
    attempt: int
    max_attempts: int
    llm_output: CustomerResearchLLMOutput | None
    draft: CustomerResearchDraft | None
    skip_reason: str | None
    error: str | None
    invocations: list[dict[str, Any]]
    validation_errors: list[str]
    status: Literal["pending", "completed", "skipped", "failed"]


class CustomerResearchAgent:
    """Runs research_customers LangGraph for one opportunity."""

    def __init__(
        self,
        llm_client: CustomerResearchLLMClient,
        settings: Settings,
        validator: CustomerResearchValidator | None = None,
    ) -> None:
        self._llm = llm_client
        self._settings = settings
        self._validator = validator or CustomerResearchValidator()
        self._graph = self._build_graph()

    async def run(self, context: OpportunityCustomerContext) -> CustomerResearchResult:
        initial_state: ResearchState = {
            "context": context,
            "attempt": 1,
            "max_attempts": self._settings.customer_research_max_retries,
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
            return {"status": "failed", "error": "missing_opportunity_title"}
        return {}

    async def _research(self, state: ResearchState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        invocation = await self._llm.research(
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

    async def _validate(self, state: ResearchState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        llm_output = state.get("llm_output")
        if llm_output is None:
            return {}

        try:
            validated = self._validator.validate(llm_output, context=state["context"])
        except CustomerResearchValidationError as exc:
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

        linked_indices = {
            item.complaint_index
            for item in validated.supporting_evidence
            if item.complaint_index is not None
        }
        linked_indices.update(
            item.complaint_index
            for item in validated.representative_complaints
            if item.complaint_index is not None
        )
        metrics = compute_validation_metrics(
            validated,
            context=state["context"],
            linked_complaint_count=len(linked_indices),
        )
        draft = CustomerResearchDraft(
            pain_score=validated.pain_score,
            urgency_score=validated.urgency_score,
            frequency_score=validated.frequency_score,
            customer_sentiment=validated.customer_sentiment,
            sentiment_score=validated.sentiment_score,
            cares_verdict=validated.cares_verdict,
            representative_complaints=validated.representative_complaints,
            supporting_evidence=validated.supporting_evidence,
            executive_summary=validated.executive_summary,
            validation_metrics=metrics,
        )
        return {"draft": draft, "status": "completed"}

    async def _finalize(self, state: ResearchState) -> dict[str, Any]:
        logger.info(
            "Customer research finished",
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

    def _to_result(self, state: ResearchState) -> CustomerResearchResult:
        status = state.get("status", "failed")
        if status == "pending":
            status = "failed"

        return CustomerResearchResult(
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
