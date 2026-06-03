"""Serialize LLM invocations with optional budget metadata."""

from __future__ import annotations

from typing import Any, Protocol


class LLMInvocationLike(Protocol):
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    cost_usd: float | None
    error: str | None
    parsed: Any
    raw_text: str | None


def serialize_llm_invocation(
    attempt: int,
    invocation: LLMInvocationLike,
    *,
    estimated_cost_usd: float | None = None,
) -> dict[str, Any]:
    return {
        "attempt": attempt,
        "model": invocation.model,
        "prompt_tokens": invocation.prompt_tokens,
        "completion_tokens": invocation.completion_tokens,
        "latency_ms": invocation.latency_ms,
        "estimated_cost_usd": estimated_cost_usd,
        "cost_usd": invocation.cost_usd,
        "error": invocation.error,
        "parsed": invocation.parsed.model_dump() if invocation.parsed else None,
        "raw_text": invocation.raw_text,
    }
