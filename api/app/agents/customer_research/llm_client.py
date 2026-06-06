"""LLM client for customer demand research."""

from __future__ import annotations

import json
import time
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agents.customer_research.schemas import (
    CustomerResearchLLMOutput,
    LLMInvocationResult,
    OpportunityCustomerContext,
)
from app.agents.openai_schema import openai_strict_json_schema
from app.config import Settings


class CustomerResearchLLMClient(Protocol):
    async def research(
        self,
        *,
        context: OpportunityCustomerContext,
        attempt: int,
    ) -> LLMInvocationResult: ...


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    if "gpt-4o-mini" in model:
        return (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
    if "gpt-4o" in model:
        return (prompt_tokens * 2.50 + completion_tokens * 10.00) / 1_000_000
    return 0.0


class OpenAICustomerResearchClient:
    """Calls OpenAI with JSON schema structured output for customer research."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for customer research")
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def research(
        self,
        *,
        context: OpportunityCustomerContext,
        attempt: int,
    ) -> LLMInvocationResult:
        started = time.perf_counter()
        system_prompt = (
            "You are a customer research analyst determining whether customers actually "
            "care about a software problem. "
            "Analyze only the provided complaint and discussion evidence from forums, "
            "reviews, and social platforms. "
            "Do NOT perform market sizing, competitor analysis, or business planning. "
            "Score pain (0-100), urgency (0-100), and frequency (0-100). "
            "Use complaint_index (the integer label on each evidence row) to reference "
            "complaints in representative_complaints and supporting_evidence. "
            "complaint_index is NOT complaint_id — never use UUID values as complaint_index. "
            "When only one complaint is listed, the only valid complaint_index is 0. "
            "Provide supporting_evidence with evidence_type from: complaint, discussion, "
            "review, forum, social. "
            "Set cares_verdict to yes, partial, or no based on whether customers genuinely "
            "care about this problem."
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._settings.customer_research_model,
                temperature=self._settings.customer_research_temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "customer_research_brief",
                        "strict": True,
                        "schema": openai_strict_json_schema(CustomerResearchLLMOutput),
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
                            f"Gap: {context.gap}\n"
                            f"Confidence: {context.confidence_score:.2f}\n\n"
                            f"Complaint evidence (use complaint_index only — not complaint_id):\n"
                            f"{self._format_evidence(context)}\n\n"
                            "Example for a single complaint: complaint_index=0 in all fields.\n"
                            "Determine whether customers care about this problem."
                        ),
                    },
                ],
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            raw_text = response.choices[0].message.content or ""
            usage = response.usage

            try:
                parsed = CustomerResearchLLMOutput.model_validate(json.loads(raw_text))
            except (json.JSONDecodeError, ValidationError) as exc:
                return LLMInvocationResult(
                    parsed=None,
                    raw_text=raw_text,
                    model=self._settings.customer_research_model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=latency_ms,
                    cost_usd=_estimate_cost_usd(
                        self._settings.customer_research_model,
                        usage.prompt_tokens if usage else 0,
                        usage.completion_tokens if usage else 0,
                    ),
                    error=f"malformed_response: {exc}",
                )

            return LLMInvocationResult(
                parsed=parsed,
                raw_text=raw_text,
                model=self._settings.customer_research_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
                cost_usd=_estimate_cost_usd(
                    self._settings.customer_research_model,
                    usage.prompt_tokens if usage else 0,
                    usage.completion_tokens if usage else 0,
                ),
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return LLMInvocationResult(
                parsed=None,
                raw_text=None,
                model=self._settings.customer_research_model,
                latency_ms=latency_ms,
                error=f"llm_error: {exc}",
            )

    @staticmethod
    def _format_evidence(context: OpportunityCustomerContext) -> str:
        if not context.complaint_evidence:
            return "No complaint evidence available."
        lines: list[str] = []
        for item in context.complaint_evidence:
            lines.append(
                f"complaint_index={item.index} "
                f"(reference id={item.complaint_id} — do NOT use as complaint_index) "
                f"source={item.source_type}/{item.source_name} url={item.url} "
                f"severity={item.severity} summary={item.summary!r} "
                f"quote={item.verbatim_quote!r}"
            )
        return "\n".join(lines)
