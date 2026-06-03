"""LLM client for human proxy founder-fit evaluation."""

from __future__ import annotations

import json
import time
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agents.human_proxy.schemas import (
    HumanProxyLLMOutput,
    LLMInvocationResult,
    OpportunityProxyContext,
)
from app.config import Settings


class HumanProxyLLMClient(Protocol):
    async def evaluate_founder_fit(
        self,
        *,
        context: OpportunityProxyContext,
        attempt: int,
    ) -> LLMInvocationResult: ...


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    if "gpt-4o-mini" in model:
        return (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
    if "gpt-4o" in model:
        return (prompt_tokens * 2.50 + completion_tokens * 10.00) / 1_000_000
    return 0.0


class OpenAIHumanProxyClient:
    """Calls OpenAI with JSON schema structured output for founder-fit evaluation."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for human proxy evaluation")
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def evaluate_founder_fit(
        self,
        *,
        context: OpportunityProxyContext,
        attempt: int,
    ) -> LLMInvocationResult:
        started = time.perf_counter()
        profile = context.founder_profile
        system_prompt = (
            "You are a human proxy evaluating whether an opportunity fits a specific "
            "founder profile. Rank founder fit and implementation feasibility based on "
            "skills, constraints, learning curve, execution complexity, and capital needs. "
            "Do NOT perform market sizing, go-to-market planning, or product roadmap design. "
            "Focus only on founder-fit and execution feasibility for the given profile. "
            "Use complaint_index to ground evidence references."
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._settings.human_proxy_model,
                temperature=self._settings.human_proxy_temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "human_proxy_evaluation",
                        "strict": True,
                        "schema": HumanProxyLLMOutput.model_json_schema(),
                    },
                },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Attempt: {attempt}\n"
                            f"Founder profile: {profile.name}\n"
                            f"Skills: {', '.join(profile.skills)}\n"
                            f"Constraints: {profile.constraints}\n"
                            f"Profile notes: {profile.description or 'none'}\n\n"
                            f"Opportunity title: {context.title}\n"
                            f"Problem: {context.problem_statement}\n"
                            f"Target user: {context.target_user}\n"
                            f"Frequency signal: {context.frequency_signal}\n"
                            f"Existing alternatives: {context.existing_alternatives}\n"
                            f"Gap: {context.gap}\n"
                            f"Confidence: {context.confidence_score:.2f}\n\n"
                            f"Complaint evidence:\n{self._format_complaints(context)}\n\n"
                            "Evaluate founder fit and feasibility."
                        ),
                    },
                ],
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            raw_text = response.choices[0].message.content or ""
            usage = response.usage

            try:
                parsed = HumanProxyLLMOutput.model_validate(json.loads(raw_text))
            except (json.JSONDecodeError, ValidationError) as exc:
                return LLMInvocationResult(
                    parsed=None,
                    raw_text=raw_text,
                    model=self._settings.human_proxy_model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=latency_ms,
                    cost_usd=_estimate_cost_usd(
                        self._settings.human_proxy_model,
                        usage.prompt_tokens if usage else 0,
                        usage.completion_tokens if usage else 0,
                    ),
                    error=f"malformed_response: {exc}",
                )

            return LLMInvocationResult(
                parsed=parsed,
                raw_text=raw_text,
                model=self._settings.human_proxy_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
                cost_usd=_estimate_cost_usd(
                    self._settings.human_proxy_model,
                    usage.prompt_tokens if usage else 0,
                    usage.completion_tokens if usage else 0,
                ),
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return LLMInvocationResult(
                parsed=None,
                raw_text=None,
                model=self._settings.human_proxy_model,
                latency_ms=latency_ms,
                error=f"llm_error: {exc}",
            )

    @staticmethod
    def _format_complaints(context: OpportunityProxyContext) -> str:
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
