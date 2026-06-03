"""LangGraph workflow for opportunity generation from a complaint pattern."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.budget_guard import serialize_llm_invocation
from app.agents.opportunity.llm_client import OpportunityLLMClient
from app.agents.opportunity.schemas import (
    ComplaintEvidence,
    ComplaintPattern,
    LLMInvocationResult,
    OpportunityDraft,
    OpportunityGenerationResult,
    OpportunityLLMOutput,
)
from app.agents.opportunity.validator import OpportunityValidationError, OpportunityValidator
from app.config import Settings
from app.logging import get_logger

if TYPE_CHECKING:
    from app.services.llm_budget import LLMBudgetService

logger = get_logger(__name__)

GRAPH_NAME = "generate_opportunity"


class GenerationState(TypedDict):
    pattern: ComplaintPattern
    evidence: list[ComplaintEvidence]
    attempt: int
    max_attempts: int
    llm_output: OpportunityLLMOutput | None
    draft: OpportunityDraft | None
    skip_reason: str | None
    error: str | None
    invocations: list[dict[str, Any]]
    validation_errors: list[str]
    status: Literal["pending", "created", "skipped", "failed"]


class OpportunityGeneratorAgent:
    """Runs generate_opportunity LangGraph for one complaint pattern."""

    def __init__(
        self,
        llm_client: OpportunityLLMClient,
        settings: Settings,
        validator: OpportunityValidator | None = None,
        budget_service: LLMBudgetService | None = None,
    ) -> None:
        self._llm = llm_client
        self._settings = settings
        self._validator = validator or OpportunityValidator()
        self._budget = budget_service
        self._graph = self._build_graph()

    async def run(
        self,
        pattern: ComplaintPattern,
        evidence: list[ComplaintEvidence],
    ) -> OpportunityGenerationResult:
        initial_state: GenerationState = {
            "pattern": pattern,
            "evidence": evidence,
            "attempt": 1,
            "max_attempts": self._settings.generation_max_retries,
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
        graph = StateGraph(GenerationState)
        graph.add_node("gather_evidence", self._gather_evidence)
        graph.add_node("synthesize", self._synthesize)
        graph.add_node("ground_check", self._ground_check)
        graph.add_node("finalize", self._finalize)

        graph.set_entry_point("gather_evidence")
        graph.add_edge("gather_evidence", "synthesize")
        graph.add_edge("synthesize", "ground_check")
        graph.add_conditional_edges(
            "ground_check",
            self._route_after_ground_check,
            {
                "retry": "synthesize",
                "finalize": "finalize",
                "fail": "finalize",
            },
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    async def _gather_evidence(self, state: GenerationState) -> dict[str, Any]:
        if not state["evidence"]:
            return {
                "status": "failed",
                "error": "no_evidence",
            }
        return {}

    async def _synthesize(self, state: GenerationState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        model = self._settings.generation_model
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

        invocation = await self._llm.synthesize(
            pattern=state["pattern"],
            evidence=state["evidence"],
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

        return {
            "invocations": invocations,
            "llm_output": invocation.parsed,
        }

    async def _ground_check(self, state: GenerationState) -> dict[str, Any]:
        if state.get("status") == "failed":
            return {}

        llm_output = state.get("llm_output")
        if llm_output is None:
            return {}

        if llm_output.confidence_score < self._settings.min_opportunity_confidence:
            return {
                "skip_reason": "low_confidence",
                "status": "skipped",
            }

        try:
            validated = self._validator.validate(
                llm_output,
                evidence=state["evidence"],
                topic=state["pattern"].topic,
            )
        except OpportunityValidationError as exc:
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

        draft = OpportunityDraft(
            title=validated.title,
            problem_statement=validated.problem_statement,
            target_user=validated.target_user,
            frequency_signal=validated.frequency_signal,
            existing_alternatives=validated.existing_alternatives,
            gap=validated.gap,
            confidence_score=validated.confidence_score,
            explanation=validated.explanation,
            complaint_ids=state["pattern"].complaint_ids,
            topic=state["pattern"].topic,
        )
        return {
            "draft": draft,
            "status": "created",
        }

    async def _finalize(self, state: GenerationState) -> dict[str, Any]:
        logger.info(
            "Opportunity generator finished",
            extra={
                "topic": state["pattern"].topic,
                "status": state.get("status"),
                "attempts": state.get("attempt"),
            },
        )
        return {}

    def _route_after_ground_check(self, state: GenerationState) -> str:
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

    def _to_result(self, state: GenerationState) -> OpportunityGenerationResult:
        status = state.get("status", "failed")
        if status == "pending":
            status = "failed"

        return OpportunityGenerationResult(
            pattern_topic=state["pattern"].topic,
            status=status,  # type: ignore[arg-type]
            draft=state.get("draft"),
            skip_reason=state.get("skip_reason"),
            error=state.get("error"),
            attempts=state.get("attempt", 0),
            eval_logs=state.get("invocations", []),
        )
