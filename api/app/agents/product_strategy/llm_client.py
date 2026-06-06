"""LLM client for product strategy planning."""

from __future__ import annotations

import json
import time
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agents.product_strategy.schemas import (
    LLMInvocationResult,
    OpportunityPlanningContext,
    ProductStrategyLLMOutput,
)
from app.agents.openai_schema import openai_strict_json_schema
from app.config import Settings


class ProductStrategyLLMClient(Protocol):
    async def plan_product(
        self,
        *,
        context: OpportunityPlanningContext,
        attempt: int,
    ) -> LLMInvocationResult: ...


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    if "gpt-4o-mini" in model:
        return (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
    if "gpt-4o" in model:
        return (prompt_tokens * 2.50 + completion_tokens * 10.00) / 1_000_000
    return 0.0


class OpenAIProductStrategyClient:
    """Calls OpenAI with JSON schema structured output for product planning."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for product strategy planning")
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def plan_product(
        self,
        *,
        context: OpportunityPlanningContext,
        attempt: int,
    ) -> LLMInvocationResult:
        started = time.perf_counter()
        system_prompt = (
            "You are a product strategist converting validated opportunities into "
            "actionable product plans. "
            "Define an MVP, core features, feature priorities, development phases, "
            "estimated timeline, and technical risks using only the provided opportunity context. "
            "Do NOT perform market sizing, revenue validation, or competitor analysis. "
            "Focus only on product planning and roadmap structure. "
            "Use complaint_index (integer label on each complaint row) in supporting_evidence. "
            "complaint_index is NOT complaint_id — never use UUID values as complaint_index. "
            "When only one complaint is listed, the only valid complaint_index is 0."
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._settings.product_strategy_model,
                temperature=self._settings.product_strategy_temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "product_strategy_plan",
                        "strict": True,
                        "schema": openai_strict_json_schema(ProductStrategyLLMOutput),
                    },
                },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Attempt: {attempt}\n"
                            f"Opportunity title: {context.title}\n"
                            f"Problem: {context.problem_statement}\n"
                            f"Target user: {context.target_user}\n"
                            f"Frequency signal: {context.frequency_signal}\n"
                            f"Existing alternatives: {context.existing_alternatives}\n"
                            f"Gap: {context.gap}\n"
                            f"Confidence: {context.confidence_score:.2f}\n\n"
                            "Complaint evidence (use complaint_index only — not complaint_id):\n"
                            f"{self._format_complaints(context)}\n\n"
                            "Example for a single complaint: complaint_index=0 in all fields.\n"
                            "Create a product strategy plan."
                        ),
                    },
                ],
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            raw_text = response.choices[0].message.content or ""
            usage = response.usage

            try:
                parsed = ProductStrategyLLMOutput.model_validate(json.loads(raw_text))
            except (json.JSONDecodeError, ValidationError) as exc:
                return LLMInvocationResult(
                    parsed=None,
                    raw_text=raw_text,
                    model=self._settings.product_strategy_model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=latency_ms,
                    cost_usd=_estimate_cost_usd(
                        self._settings.product_strategy_model,
                        usage.prompt_tokens if usage else 0,
                        usage.completion_tokens if usage else 0,
                    ),
                    error=f"malformed_response: {exc}",
                )

            return LLMInvocationResult(
                parsed=parsed,
                raw_text=raw_text,
                model=self._settings.product_strategy_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
                cost_usd=_estimate_cost_usd(
                    self._settings.product_strategy_model,
                    usage.prompt_tokens if usage else 0,
                    usage.completion_tokens if usage else 0,
                ),
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return LLMInvocationResult(
                parsed=None,
                raw_text=None,
                model=self._settings.product_strategy_model,
                latency_ms=latency_ms,
                error=f"llm_error: {exc}",
            )

    @staticmethod
    def _format_complaints(context: OpportunityPlanningContext) -> str:
        if not context.complaint_evidence:
            return "No complaint evidence available."
        lines = []
        for item in context.complaint_evidence:
            products = ", ".join(item.product_mentions) if item.product_mentions else "none"
            lines.append(
                f"{item.index}. summary={item.summary!r} severity={item.severity} "
                f"products={products} quote={item.verbatim_quote!r}"
            )
        return "\n".join(lines)
