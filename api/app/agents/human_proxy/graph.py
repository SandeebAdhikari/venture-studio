"""LangGraph workflow for human proxy founder-fit evaluation."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.human_proxy.llm_client import HumanProxyLLMClient
from app.agents.human_proxy.metrics import compute_evaluation_metrics
from app.agents.human_proxy.schemas import (
    HumanProxyDraft,
    HumanProxyLLMOutput,
    HumanProxyResult,
    LLMInvocationResult,
    OpportunityProxyContext,
)
from app.agents.human_proxy.validator import HumanProxyValidationError, HumanProxyValidator
from app.config import Settings
from app.logging import get_logger

logger = get_logger(__name__)

GRAPH_NAME = "evaluate_human_proxy"


class ProxyState(TypedDict):
    context: OpportunityProxyContext
    attempt: int
    max_attempts: int
    llm_output: HumanProxyLLMOutput | None
    draft: HumanProxyDraft | None
    skip_reason: str | None
    error: str | None
    invocations: list[dict[str, Any]]
    validation_errors: list[str]
    status: Literal["pending", "completed", "skipped", "failed"]


class HumanProxyAgent:
    def __init__(
        self,
        llm_client: HumanProxyLLMClient,
        settings: Settings,
        validator: HumanProxyValidator | None = None,
    ) -> None:
        self._llm = llm_client
        self._settings = settings
        self._validator = validator or HumanProxyValidator()
        self._graph = self._build_graph()

    async def run(self, context: OpportunityProxyContext) -> HumanProxyResult:
        initial_state: ProxyState = {
            "context": context,
            "attempt": 1,
            "max_attempts": self._settings.human_proxy_max_retries,
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
        graph = StateGraph(ProxyState)
        graph.add_node("gather_context", self._gather_context)
        graph.add_node("evaluate_founder_fit", self._evaluate_founder_fit)
        graph.add_node("check", self._check)
        graph.add_node("finalize", self._finalize)

        graph.set_entry_point("gather_context")
        graph.add_edge("gather_context", "evaluate_founder_fit")
        graph.add_edge("evaluate_founder_fit", "check")
        graph.add_conditional_edges(
            "check",
            self._route_after_check,
            {"retry": "evaluate_founder_fit", "finalize": "finalize", "fail": "finalize"},
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    async def _gather_context(self, state: ProxyState) -> dict[str, Any]:
        if not state["context"].title.strip():
            return {"status": "failed", "error": "missing_opportunity_title"}
        if not state["context"].founder_profile.skills:
            return {"status": "failed", "error": "missing_founder_skills"}
        return {}

    async def _evaluate_founder_fit(self, state: ProxyState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        invocation = await self._llm.evaluate_founder_fit(
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

    async def _check(self, state: ProxyState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        llm_output = state.get("llm_output")
        if llm_output is None:
            return {}

        try:
            validated = self._validator.validate(llm_output, context=state["context"])
        except HumanProxyValidationError as exc:
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

        metrics = compute_evaluation_metrics(validated)
        draft = HumanProxyDraft(
            founder_fit_score=validated.founder_fit_score,
            feasibility_score=validated.feasibility_score,
            recommendation=validated.recommendation,
            founder_fit_analysis=validated.founder_fit_analysis,
            implementation_feasibility=validated.implementation_feasibility,
            learning_curve=validated.learning_curve,
            execution_complexity=validated.execution_complexity,
            capital_requirements=validated.capital_requirements,
            supporting_evidence=validated.supporting_evidence,
            executive_summary=validated.executive_summary,
            evaluation_metrics=metrics,
        )
        return {"draft": draft, "status": "completed"}

    async def _finalize(self, state: ProxyState) -> dict[str, Any]:
        logger.info(
            "Human proxy evaluation finished",
            extra={
                "opportunity_id": str(state["context"].opportunity_id),
                "founder_profile_id": str(state["context"].founder_profile.founder_profile_id),
                "status": state.get("status"),
                "attempts": state.get("attempt"),
            },
        )
        return {}

    def _route_after_check(self, state: ProxyState) -> str:
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

    def _to_result(self, state: ProxyState) -> HumanProxyResult:
        status = state.get("status", "failed")
        if status == "pending":
            status = "failed"

        return HumanProxyResult(
            opportunity_id=state["context"].opportunity_id,
            founder_profile_id=state["context"].founder_profile.founder_profile_id,
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
