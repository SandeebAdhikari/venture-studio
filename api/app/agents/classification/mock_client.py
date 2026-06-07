"""Mock LLM client for classification tests."""

from __future__ import annotations

from app.agents.classification.llm_client import LLMInvocationResult
from app.agents.classification.schemas import ClassificationLLMOutput


class MockClassificationLLMClient:
    """Returns scripted responses in call order."""

    def __init__(
        self,
        responses: list[LLMInvocationResult | ClassificationLLMOutput | None],
        *,
        model: str = "mock-classifier",
    ) -> None:
        self._responses = list(responses)
        self._index = 0
        self._model = model
        self.call_count = 0

    async def classify(
        self,
        *,
        title: str | None,
        body: str,
        attempt: int,
        neighborhood=None,
    ) -> LLMInvocationResult:
        self.call_count += 1
        if self._index >= len(self._responses):
            return LLMInvocationResult(
                parsed=None,
                raw_text=None,
                model=self._model,
                error="no_more_mock_responses",
            )

        response = self._responses[self._index]
        self._index += 1

        if response is None:
            return LLMInvocationResult(
                parsed=None,
                raw_text="not valid json",
                model=self._model,
                error="malformed_response: invalid JSON",
            )

        if isinstance(response, ClassificationLLMOutput):
            return LLMInvocationResult(
                parsed=response,
                raw_text=response.model_dump_json(),
                model=self._model,
                prompt_tokens=100,
                completion_tokens=50,
                latency_ms=10,
                cost_usd=0.0,
            )

        return response
