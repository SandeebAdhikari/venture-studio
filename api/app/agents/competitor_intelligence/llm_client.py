"""LLM client for competitor intelligence analysis."""

from __future__ import annotations

import json
import time
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agents.competitor_intelligence.schemas import (
    CompetitorAnalysisLLMOutput,
    LLMInvocationResult,
    OpportunityCompetitorContext,
)
from app.agents.openai_schema import openai_strict_json_schema
from app.config import Settings


class CompetitorIntelligenceLLMClient(Protocol):
    async def analyze(
        self,
        *,
        context: OpportunityCompetitorContext,
        attempt: int,
    ) -> LLMInvocationResult: ...


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    if "gpt-4o-mini" in model:
        return (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
    if "gpt-4o" in model:
        return (prompt_tokens * 2.50 + completion_tokens * 10.00) / 1_000_000
    return 0.0


class OpenAICompetitorIntelligenceClient:
    """Calls OpenAI with JSON schema structured output for competitor analysis."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for competitor intelligence")
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def analyze(
        self,
        *,
        context: OpportunityCompetitorContext,
        attempt: int,
    ) -> LLMInvocationResult:
        started = time.perf_counter()
        system_prompt = (
            "You are a competitor intelligence analyst for software business opportunities. "
            "Analyze competitors only — do NOT perform market sizing, TAM/SAM research, "
            "or business planning. "
            "For each competitor provide: positioning, pricing model, strengths, weaknesses, "
            "customer complaint themes, and review sentiment. "
            "Identify competitive gaps the opportunity could exploit. "
            "Prioritize products mentioned in the opportunity evidence when known. "
            "Use structured pricing fields and explicit sentiment scores from -1 (negative) "
            "to 1 (positive)."
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._settings.competitor_model,
                temperature=self._settings.competitor_temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "competitor_intelligence",
                        "strict": True,
                        "schema": openai_strict_json_schema(CompetitorAnalysisLLMOutput),
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
                            f"Known products from evidence: "
                            f"{', '.join(context.known_products) or 'none'}\n"
                            f"Product mentions: "
                            f"{', '.join(context.product_mentions) or 'none'}\n\n"
                            f"Complaint summaries:\n"
                            f"{self._format_complaints(context.complaint_summaries)}\n\n"
                            "Analyze the competitive landscape for this opportunity."
                        ),
                    },
                ],
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            raw_text = response.choices[0].message.content or ""
            usage = response.usage

            try:
                parsed = CompetitorAnalysisLLMOutput.model_validate(json.loads(raw_text))
            except (json.JSONDecodeError, ValidationError) as exc:
                return LLMInvocationResult(
                    parsed=None,
                    raw_text=raw_text,
                    model=self._settings.competitor_model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=latency_ms,
                    cost_usd=_estimate_cost_usd(
                        self._settings.competitor_model,
                        usage.prompt_tokens if usage else 0,
                        usage.completion_tokens if usage else 0,
                    ),
                    error=f"malformed_response: {exc}",
                )

            return LLMInvocationResult(
                parsed=parsed,
                raw_text=raw_text,
                model=self._settings.competitor_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
                cost_usd=_estimate_cost_usd(
                    self._settings.competitor_model,
                    usage.prompt_tokens if usage else 0,
                    usage.completion_tokens if usage else 0,
                ),
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return LLMInvocationResult(
                parsed=None,
                raw_text=None,
                model=self._settings.competitor_model,
                latency_ms=latency_ms,
                error=f"llm_error: {exc}",
            )

    @staticmethod
    def _format_complaints(summaries: list[str]) -> str:
        if not summaries:
            return "No linked complaints."
        lines = [f"{index}. {summary}" for index, summary in enumerate(summaries[:15], start=1)]
        if len(summaries) > 15:
            lines.append(f"... and {len(summaries) - 15} more complaints")
        return "\n".join(lines)
