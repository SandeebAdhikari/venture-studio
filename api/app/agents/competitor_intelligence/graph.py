"""LangGraph workflow for competitor intelligence analysis."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.competitor_intelligence.llm_client import CompetitorIntelligenceLLMClient
from app.agents.competitor_intelligence.metrics import compute_evaluation_metrics
from app.agents.competitor_intelligence.schemas import (
    CompetitorAnalysisDraft,
    CompetitorAnalysisLLMOutput,
    CompetitorAnalysisResult,
    CompetitorProfileDraft,
    LLMInvocationResult,
    OpportunityCompetitorContext,
)
from app.agents.competitor_intelligence.validator import (
    CompetitorAnalysisValidator,
    CompetitorValidationError,
)
from app.config import Settings
from app.logging import get_logger

logger = get_logger(__name__)

GRAPH_NAME = "analyze_competitors"


class AnalysisState(TypedDict):
    context: OpportunityCompetitorContext
    attempt: int
    max_attempts: int
    llm_output: CompetitorAnalysisLLMOutput | None
    draft: CompetitorAnalysisDraft | None
    skip_reason: str | None
    error: str | None
    invocations: list[dict[str, Any]]
    validation_errors: list[str]
    status: Literal["pending", "completed", "skipped", "failed"]


class CompetitorIntelligenceAgent:
    """Runs analyze_competitors LangGraph for one opportunity."""

    def __init__(
        self,
        llm_client: CompetitorIntelligenceLLMClient,
        settings: Settings,
        validator: CompetitorAnalysisValidator | None = None,
    ) -> None:
        self._llm = llm_client
        self._settings = settings
        self._validator = validator or CompetitorAnalysisValidator()
        self._graph = self._build_graph()

    async def run(self, context: OpportunityCompetitorContext) -> CompetitorAnalysisResult:
        initial_state: AnalysisState = {
            "context": context,
            "attempt": 1,
            "max_attempts": self._settings.competitor_max_retries,
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
        graph = StateGraph(AnalysisState)
        graph.add_node("gather_context", self._gather_context)
        graph.add_node("analyze", self._analyze)
        graph.add_node("validate", self._validate)
        graph.add_node("finalize", self._finalize)

        graph.set_entry_point("gather_context")
        graph.add_edge("gather_context", "analyze")
        graph.add_edge("analyze", "validate")
        graph.add_conditional_edges(
            "validate",
            self._route_after_validate,
            {
                "retry": "analyze",
                "finalize": "finalize",
                "fail": "finalize",
            },
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    async def _gather_context(self, state: AnalysisState) -> dict[str, Any]:
        if not state["context"].title.strip():
            return {
                "status": "failed",
                "error": "missing_opportunity_title",
            }
        return {}

    async def _analyze(self, state: AnalysisState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        invocation = await self._llm.analyze(
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

        return {
            "invocations": invocations,
            "llm_output": invocation.parsed,
        }

    async def _validate(self, state: AnalysisState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        llm_output = state.get("llm_output")
        if llm_output is None:
            return {}

        try:
            validated = self._validator.validate(llm_output, context=state["context"])
        except CompetitorValidationError as exc:
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
        competitors = [
            CompetitorProfileDraft(
                name=competitor.name,
                positioning=competitor.positioning,
                pricing=competitor.pricing,
                strengths=competitor.strengths,
                weaknesses=competitor.weaknesses,
                customer_complaints=competitor.customer_complaints,
                review_sentiment=competitor.review_sentiment,
                sentiment_score=competitor.sentiment_score,
                source_basis=competitor.source_basis,
            )
            for competitor in validated.competitors
        ]
        draft = CompetitorAnalysisDraft(
            competitors=competitors,
            competitive_gaps=validated.competitive_gaps,
            executive_summary=validated.executive_summary,
            evaluation_metrics=metrics,
        )
        return {
            "draft": draft,
            "status": "completed",
        }

    async def _finalize(self, state: AnalysisState) -> dict[str, Any]:
        logger.info(
            "Competitor intelligence finished",
            extra={
                "opportunity_id": str(state["context"].opportunity_id),
                "status": state.get("status"),
                "attempts": state.get("attempt"),
            },
        )
        return {}

    def _route_after_validate(self, state: AnalysisState) -> str:
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

    def _to_result(self, state: AnalysisState) -> CompetitorAnalysisResult:
        status = state.get("status", "failed")
        if status == "pending":
            status = "failed"

        return CompetitorAnalysisResult(
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
