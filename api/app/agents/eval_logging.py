"""Shared helpers for persisting agent LLM evaluation logs."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.repositories import RepositoryContainer
from app.services.llm_budget import LLMBudgetService


class AgentEvalResult(Protocol):
    status: str
    attempts: int
    eval_logs: list[dict[str, Any]]


async def persist_agent_eval_logs(
    repos: RepositoryContainer,
    *,
    budget: LLMBudgetService | None,
    entity_type: str,
    entity_id: UUID,
    graph_name: str,
    default_model: str,
    agent_result: AgentEvalResult,
    eval_metadata_extra: dict[str, Any] | None = None,
) -> None:
    extra = eval_metadata_extra or {}
    for log in agent_result.eval_logs:
        status = "success" if log.get("error") is None else "error"
        await repos.llm_calls.log_agent_call(
            entity_type=entity_type,
            entity_id=entity_id,
            graph_name=graph_name,
            model=log.get("model", default_model),
            attempt=int(log.get("attempt", 1)),
            prompt_tokens=int(log.get("prompt_tokens", 0)),
            completion_tokens=int(log.get("completion_tokens", 0)),
            estimated_cost_usd=log.get("estimated_cost_usd"),
            latency_ms=log.get("latency_ms"),
            cost_usd=log.get("cost_usd"),
            status=status,
            error_detail=log.get("error"),
            eval_metadata={
                "parsed": log.get("parsed"),
                "raw_text": log.get("raw_text"),
                "agent_status": agent_result.status,
                "attempts": agent_result.attempts,
                **extra,
            },
        )
        if budget is not None:
            await budget.after_call_recorded()
