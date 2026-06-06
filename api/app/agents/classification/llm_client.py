"""LLM client for structured complaint classification."""

from __future__ import annotations

import json
import time
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agents.classification.schemas import ClassificationLLMOutput, LLMInvocationResult
from app.agents.openai_schema import openai_strict_json_schema
from app.agents.classification.problem_category_alignment import alignment_prompt_block
from app.agents.classification.taxonomy import taxonomy_prompt_block
from app.agents.classification.founder_signals import founder_signals_prompt_block
from app.config import Settings


class ClassificationLLMClient(Protocol):
    async def classify(
        self,
        *,
        title: str | None,
        body: str,
        attempt: int,
    ) -> LLMInvocationResult: ...


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    # gpt-4o-mini approximate pricing (USD per 1M tokens).
    if "gpt-4o-mini" in model:
        return (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000
    if "gpt-4o" in model:
        return (prompt_tokens * 2.50 + completion_tokens * 10.00) / 1_000_000
    return 0.0


class OpenAIClassificationClient:
    """Calls OpenAI with JSON schema structured output."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for classification")
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def classify(
        self,
        *,
        title: str | None,
        body: str,
        attempt: int,
    ) -> LLMInvocationResult:
        started = time.perf_counter()
        user_content = self._format_user_content(title=title, body=body)
        system_prompt = (
            "You classify raw user text into structured complaint metadata. "
            "If the text is not a complaint, set is_complaint to false "
            "and still return valid enum codes. "
            "Use 'other' codes when uncertain.\n\n"
            f"{alignment_prompt_block()}\n\n"
            f"{taxonomy_prompt_block()}\n\n"
            f"{founder_signals_prompt_block()}"
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._settings.classification_model,
                temperature=self._settings.classification_temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "complaint_classification",
                        "strict": True,
                        "schema": openai_strict_json_schema(ClassificationLLMOutput),
                    },
                },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Attempt: {attempt}\n"
                            f"Classify the following text:\n\n{user_content}"
                        ),
                    },
                ],
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            choice = response.choices[0]
            raw_text = choice.message.content or ""
            usage = response.usage

            try:
                parsed = ClassificationLLMOutput.model_validate(json.loads(raw_text))
            except (json.JSONDecodeError, ValidationError) as exc:
                return LLMInvocationResult(
                    parsed=None,
                    raw_text=raw_text,
                    model=self._settings.classification_model,
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    latency_ms=latency_ms,
                    cost_usd=_estimate_cost_usd(
                        self._settings.classification_model,
                        usage.prompt_tokens if usage else 0,
                        usage.completion_tokens if usage else 0,
                    ),
                    error=f"malformed_response: {exc}",
                )

            return LLMInvocationResult(
                parsed=parsed,
                raw_text=raw_text,
                model=self._settings.classification_model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                latency_ms=latency_ms,
                cost_usd=_estimate_cost_usd(
                    self._settings.classification_model,
                    usage.prompt_tokens if usage else 0,
                    usage.completion_tokens if usage else 0,
                ),
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return LLMInvocationResult(
                parsed=None,
                raw_text=None,
                model=self._settings.classification_model,
                latency_ms=latency_ms,
                error=f"llm_error: {exc}",
            )

    @staticmethod
    def _format_user_content(*, title: str | None, body: str) -> str:
        if title:
            return f"Title: {title}\n\nBody: {body}"
        return body
