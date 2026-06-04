"""LLM client for market intelligence research."""

from __future__ import annotations

import json
import time
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agents.openai_schema import openai_strict_json_schema
from app.agents.market_research.schemas import (
    LLMInvocationResult,
    MarketResearchLLMOutput,
    OpportunityResearchContext,
)
from app.config import Settings


class MarketResearchLLMClient(Protocol):
    async def research(
        self,
        *,
        context: OpportunityResearchContext,
        attempt: int,
    ) -> LLMInvocationResult: ...


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    if "gpt-4o-mini" in model:
        return (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
    if "gpt-4o" in model:
        return (prompt_tokens * 2.50 + completion_tokens * 10.00) / 1_000_000
    return 0.0


class OpenAIMarketResearchClient:
    """Calls OpenAI with JSON schema structured output for market intelligence."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for market research")
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def research(
        self,
        *,
        context: OpportunityResearchContext,
        attempt: int,
    ) -> LLMInvocationResult:
        started = time.perf_counter()
        system_prompt = (
            "You are a market intelligence analyst for software business opportunities. "
            "Produce structured market sizing and industry analysis only. "
            "Do NOT perform competitor analysis — do not name, compare, or profile specific "
            "companies or products. "
            "Do NOT produce business plans, MVP roadmaps, GTM strategy, or pricing advice. "
            "Estimate market_size_usd, tam_usd, sam_usd, and industry_growth_rate_pct using "
            "public industry knowledge and the opportunity context. "
            "Label each supporting_evidence item with an appropriate source_type and "
            "source_reference. Use inference_from_complaints when reasoning from complaint "
            "patterns. Be explicit about uncertainty via confidence levels."
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._settings.research_model,
                temperature=self._settings.research_temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "market_intelligence_brief",
                        "strict": True,
                        "schema": openai_strict_json_schema(MarketResearchLLMOutput),
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
                            f"Existing alternatives (from complaints): "
                            f"{context.existing_alternatives}\n"
                            f"Gap: {context.gap}\n"
                            f"Confidence: {context.confidence_score:.2f}\n"
                            f"Domains: {', '.join(context.domain_codes) or 'unknown'}\n"
                            f"Categories: {', '.join(context.category_codes) or 'unknown'}\n"
                            f"Personas: {', '.join(context.persona_codes) or 'unknown'}\n\n"
                            f"Complaint summaries:\n"
                            f"{self._format_complaints(context.complaint_summaries)}\n\n"
                            "Research market intelligence for this opportunity."
                        ),
                    },
                ],
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            raw_text = response.choices[0].message.content or ""
            usage = response.usage

            try:
                parsed = MarketResearchLLMOutput.model_validate(json.loads(raw_text))
            except (json.JSONDecodeError, ValidationError) as exc:
                return LLMInvocationResult(
                    parsed=None,
                    raw_text=raw_text,
                    model=self._settings.research_model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=latency_ms,
                    cost_usd=_estimate_cost_usd(
                        self._settings.research_model,
                        usage.prompt_tokens if usage else 0,
                        usage.completion_tokens if usage else 0,
                    ),
                    error=f"malformed_response: {exc}",
                )

            return LLMInvocationResult(
                parsed=parsed,
                raw_text=raw_text,
                model=self._settings.research_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
                cost_usd=_estimate_cost_usd(
                    self._settings.research_model,
                    usage.prompt_tokens if usage else 0,
                    usage.completion_tokens if usage else 0,
                ),
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return LLMInvocationResult(
                parsed=None,
                raw_text=None,
                model=self._settings.research_model,
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
