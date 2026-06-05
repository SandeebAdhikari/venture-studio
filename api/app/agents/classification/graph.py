"""LangGraph workflow for complaint classification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.agents.budget_guard import serialize_llm_invocation
from app.agents.classification.llm_client import ClassificationLLMClient
from app.agents.classification.schemas import (
    ClassificationAgentResult,
    ClassificationLLMOutput,
    ClassificationResult,
    LLMInvocationResult,
    RawComplaintText,
)
from app.agents.classification.source_text import build_classification_source_text
from app.agents.classification.validator import (
    ClassificationValidationError,
    ClassificationValidator,
)
from app.config import Settings
from app.logging import get_logger

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)

GRAPH_NAME = "classify_complaint"


class ClassificationState(TypedDict):
    signal_id: UUID | None
    title: str | None
    body: str
    url: str | None
    attempt: int
    max_attempts: int
    llm_output: ClassificationLLMOutput | None
    classification: ClassificationResult | None
    is_complaint: bool
    skip_reason: str | None
    error: str | None
    invocations: list[dict[str, Any]]
    validation_errors: list[str]
    status: Literal["pending", "classified", "skipped", "failed"]


class ComplaintClassificationAgent:
    """Runs the classify_complaint LangGraph with retry on malformed/invalid output."""

    def __init__(
        self,
        llm_client: ClassificationLLMClient,
        settings: Settings,
        validator: ClassificationValidator | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._llm = llm_client
        self._settings = settings
        self._validator = validator or ClassificationValidator()
        self._budget = budget_service
        self._graph = self._build_graph()

    async def run(self, raw: RawComplaintText) -> ClassificationAgentResult:
        initial_state: ClassificationState = {
            "signal_id": raw.signal_id,
            "title": raw.title,
            "body": raw.body,
            "url": raw.url,
            "attempt": 1,
            "max_attempts": self._settings.classification_max_retries,
            "llm_output": None,
            "classification": None,
            "is_complaint": False,
            "skip_reason": None,
            "error": None,
            "invocations": [],
            "validation_errors": [],
            "status": "pending",
        }
        final_state = await self._graph.ainvoke(initial_state)
        return self._to_agent_result(final_state)

    def _build_graph(self):
        graph = StateGraph(ClassificationState)
        graph.add_node("extract", self._extract)
        graph.add_node("validate", self._validate)
        graph.add_node("finalize", self._finalize)

        graph.set_entry_point("extract")
        graph.add_edge("extract", "validate")
        graph.add_conditional_edges(
            "validate",
            self._route_after_validate,
            {
                "retry": "extract",
                "finalize": "finalize",
                "fail": "finalize",
            },
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    async def _extract(self, state: ClassificationState) -> dict[str, Any]:
        model = self._settings.classification_model
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
                }

        invocation = await self._llm.classify(
            title=state["title"],
            body=state["body"],
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
            }

        return {
            "invocations": invocations,
            "llm_output": invocation.parsed,
        }

    async def _validate(self, state: ClassificationState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        llm_output = state.get("llm_output")
        if llm_output is None:
            return {}

        if not llm_output.is_complaint:
            return {
                "is_complaint": False,
                "skip_reason": "not_a_complaint",
                "status": "skipped",
            }

        source_text = self._source_text(state["title"], state["body"])
        try:
            validated = self._validator.validate(llm_output, source_text=source_text)
        except ClassificationValidationError as exc:
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

        classification = ClassificationResult(
            industry=validated.industry,
            customer_type=validated.customer_type,
            problem_category=validated.problem_category,
            severity_score=validated.severity_score,
            summary=validated.summary,
            is_complaint=True,
            verbatim_quote=validated.verbatim_quote,
            confidence=validated.confidence,
            product_mentions=validated.product_mentions,
            business_function_code=validated.business_function_code,
            jtbd_code=validated.jtbd_code,
            consequence_code=validated.consequence_code,
        )
        return {
            "is_complaint": True,
            "classification": classification,
            "status": "classified",
        }

    async def _finalize(self, state: ClassificationState) -> dict[str, Any]:
        logger.info(
            "Classification agent finished",
            extra={
                "signal_id": str(state["signal_id"]) if state.get("signal_id") else None,
                "status": state.get("status"),
                "attempts": state.get("attempt"),
                "validation_errors": state.get("validation_errors"),
            },
        )
        return {}

    def _route_after_validate(self, state: ClassificationState) -> str:
        if state.get("status") == "failed":
            return "fail"
        if state.get("status") == "skipped":
            return "finalize"
        if state.get("classification") is not None:
            return "finalize"
        if state.get("llm_output") is None and state["attempt"] <= state["max_attempts"]:
            return "retry"
        if state.get("validation_errors") and state["attempt"] <= state["max_attempts"]:
            return "retry"
        return "fail"

    def _to_agent_result(self, state: ClassificationState) -> ClassificationAgentResult:
        status = state.get("status", "failed")
        if status == "pending":
            status = "failed"

        return ClassificationAgentResult(
            signal_id=state.get("signal_id"),
            status=status,  # type: ignore[arg-type]
            classification=state.get("classification"),
            skip_reason=state.get("skip_reason"),
            error=state.get("error"),
            attempts=state.get("attempt", 0),
            eval_logs=state.get("invocations", []),
        )

    @staticmethod
    def _source_text(title: str | None, body: str) -> str:
        return build_classification_source_text(title=title, body=body)
