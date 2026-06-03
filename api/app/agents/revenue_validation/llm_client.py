"""LLM client for revenue validation."""

from __future__ import annotations

import json
import time
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agents.revenue_validation.schemas import (
    LLMInvocationResult,
    OpportunityRevenueContext,
    RevenueValidationLLMOutput,
)
from app.config import Settings


class RevenueValidationLLMClient(Protocol):
    async def validate_revenue(
        self,
        *,
        context: OpportunityRevenueContext,
        attempt: int,
    ) -> LLMInvocationResult: ...


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    if "gpt-4o-mini" in model:
        return (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
    if "gpt-4o" in model:
        return (prompt_tokens * 2.50 + completion_tokens * 10.00) / 1_000_000
    return 0.0


class OpenAIRevenueValidationClient:
    """Calls OpenAI with JSON schema structured output for revenue validation."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for revenue validation")
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def validate_revenue(
        self,
        *,
        context: OpportunityRevenueContext,
        attempt: int,
    ) -> LLMInvocationResult:
        started = time.perf_counter()
        system_prompt = (
            "You are a revenue validation analyst determining whether customers are "
            "willing to pay for a software opportunity. "
            "Analyze existing spending signals, competitor pricing, budget availability, "
            "buyer profiles, and purchasing frequency using only provided evidence. "
            "Do NOT perform market sizing, competitor deep-dives, or business planning. "
            "Focus only on willingness-to-pay, pricing recommendations, and revenue confidence. "
            "Use complaint_index and competitor_index to ground evidence references."
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._settings.revenue_validation_model,
                temperature=self._settings.revenue_validation_temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "revenue_validation_brief",
                        "strict": True,
                        "schema": RevenueValidationLLMOutput.model_json_schema(),
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
                            f"Existing alternatives: {context.existing_alternatives}\n"
                            f"Gap: {context.gap}\n"
                            f"Confidence: {context.confidence_score:.2f}\n\n"
                            f"Complaint evidence:\n{self._format_complaints(context)}\n\n"
                            f"Competitor pricing:\n{self._format_competitors(context)}\n\n"
                            "Validate revenue potential and willingness to pay."
                        ),
                    },
                ],
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            raw_text = response.choices[0].message.content or ""
            usage = response.usage

            try:
                parsed = RevenueValidationLLMOutput.model_validate(json.loads(raw_text))
            except (json.JSONDecodeError, ValidationError) as exc:
                return LLMInvocationResult(
                    parsed=None,
                    raw_text=raw_text,
                    model=self._settings.revenue_validation_model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=latency_ms,
                    cost_usd=_estimate_cost_usd(
                        self._settings.revenue_validation_model,
                        usage.prompt_tokens if usage else 0,
                        usage.completion_tokens if usage else 0,
                    ),
                    error=f"malformed_response: {exc}",
                )

            return LLMInvocationResult(
                parsed=parsed,
                raw_text=raw_text,
                model=self._settings.revenue_validation_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
                cost_usd=_estimate_cost_usd(
                    self._settings.revenue_validation_model,
                    usage.prompt_tokens if usage else 0,
                    usage.completion_tokens if usage else 0,
                ),
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return LLMInvocationResult(
                parsed=None,
                raw_text=None,
                model=self._settings.revenue_validation_model,
                latency_ms=latency_ms,
                error=f"llm_error: {exc}",
            )

    @staticmethod
    def _format_complaints(context: OpportunityRevenueContext) -> str:
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

    @staticmethod
    def _format_competitors(context: OpportunityRevenueContext) -> str:
        if not context.competitor_pricing:
            return "No competitor pricing context available."
        lines = []
        for item in context.competitor_pricing:
            lines.append(
                f"{item.index}. name={item.name} positioning={item.positioning!r} "
                f"pricing={item.pricing_model}"
            )
        return "\n".join(lines)
