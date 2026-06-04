"""LLM client for opportunity synthesis."""

from __future__ import annotations

import json
import time
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agents.openai_schema import openai_strict_json_schema
from app.agents.opportunity.schemas import (
    ComplaintEvidence,
    ComplaintPattern,
    LLMInvocationResult,
    OpportunityLLMOutput,
)
from app.config import Settings


class OpportunityLLMClient(Protocol):
    async def synthesize(
        self,
        *,
        pattern: ComplaintPattern,
        evidence: list[ComplaintEvidence],
        attempt: int,
        validation_errors: list[str] | None = None,
    ) -> LLMInvocationResult: ...


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    if "gpt-4o-mini" in model:
        return (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
    if "gpt-4o" in model:
        return (prompt_tokens * 2.50 + completion_tokens * 10.00) / 1_000_000
    return 0.0


class OpenAIOpportunityClient:
    """Calls OpenAI with JSON schema structured output."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for opportunity generation")
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def synthesize(
        self,
        *,
        pattern: ComplaintPattern,
        evidence: list[ComplaintEvidence],
        attempt: int,
        validation_errors: list[str] | None = None,
    ) -> LLMInvocationResult:
        started = time.perf_counter()
        system_prompt = (
            "You synthesize software business opportunities from recurring complaint patterns. "
            "Use only evidence from the provided complaints. "
            "Do not invent market size, funding data, or competitor names "
            "not present in the evidence. "
            "No market research — evidence only."
        )
        evidence_block = self._format_evidence(evidence)
        retry_block = ""
        if validation_errors:
            retry_block = (
                "\n\nPrevious validation errors (fix these in your response):\n"
                + "\n".join(f"- {err}" for err in validation_errors)
            )

        try:
            response = await self._client.chat.completions.create(
                model=self._settings.generation_model,
                temperature=self._settings.generation_temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "opportunity_brief",
                        "strict": True,
                        "schema": openai_strict_json_schema(OpportunityLLMOutput),
                    },
                },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Attempt: {attempt}\n"
                            f"Topic pattern: {pattern.topic}\n"
                            f"Anchor phrase: {pattern.anchor_phrase}\n"
                            f"Complaint count: {pattern.complaint_count}\n"
                            f"Average severity: {pattern.avg_severity:.1f}\n"
                            f"Dominant domain: {pattern.domain_code}\n"
                            f"Dominant category: {pattern.category_code}\n"
                            f"Dominant persona: {pattern.dominant_persona_code}\n\n"
                            f"Evidence:\n{evidence_block}\n\n"
                            "Generate a specific SaaS wedge opportunity title and brief. "
                            "If no products appear in evidence, write "
                            "'No named products in evidence' for existing_alternatives "
                            "(do not use the word None as a product name)."
                            f"{retry_block}"
                        ),
                    },
                ],
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            raw_text = response.choices[0].message.content or ""
            usage = response.usage

            try:
                parsed = OpportunityLLMOutput.model_validate(json.loads(raw_text))
            except (json.JSONDecodeError, ValidationError) as exc:
                return LLMInvocationResult(
                    parsed=None,
                    raw_text=raw_text,
                    model=self._settings.generation_model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=latency_ms,
                    cost_usd=_estimate_cost_usd(
                        self._settings.generation_model,
                        usage.prompt_tokens if usage else 0,
                        usage.completion_tokens if usage else 0,
                    ),
                    error=f"malformed_response: {exc}",
                )

            return LLMInvocationResult(
                parsed=parsed,
                raw_text=raw_text,
                model=self._settings.generation_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
                cost_usd=_estimate_cost_usd(
                    self._settings.generation_model,
                    usage.prompt_tokens if usage else 0,
                    usage.completion_tokens if usage else 0,
                ),
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return LLMInvocationResult(
                parsed=None,
                raw_text=None,
                model=self._settings.generation_model,
                latency_ms=latency_ms,
                error=f"llm_error: {exc}",
            )

    @staticmethod
    def _format_evidence(evidence: list[ComplaintEvidence]) -> str:
        lines: list[str] = []
        for index, item in enumerate(evidence[:20], start=1):
            products = ", ".join(item.product_mentions) if item.product_mentions else "none"
            lines.append(
                f"{index}. summary={item.summary!r} "
                f"severity={item.severity} persona={item.persona_code} "
                f"products={products} quote={item.verbatim_quote!r}"
            )
        if len(evidence) > 20:
            lines.append(f"... and {len(evidence) - 20} more complaints")
        return "\n".join(lines)
