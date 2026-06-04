"""Mock LLM client for opportunity generation tests."""

from __future__ import annotations

from app.agents.opportunity.llm_client import LLMInvocationResult
from app.agents.opportunity.schemas import ComplaintEvidence, ComplaintPattern, OpportunityLLMOutput


class MockOpportunityLLMClient:
    """Returns scripted synthesis responses in call order or by topic."""

    def __init__(
        self,
        responses: list[OpportunityLLMOutput | None] | dict[str, OpportunityLLMOutput],
        *,
        model: str = "mock-generator",
    ) -> None:
        if isinstance(responses, dict):
            self._by_topic = responses
            self._responses: list[OpportunityLLMOutput | None] = []
        else:
            self._by_topic = {}
            self._responses = list(responses)
        self._index = 0
        self._model = model
        self.call_count = 0
        self.last_validation_errors: list[str] | None = None

    async def synthesize(
        self,
        *,
        pattern: ComplaintPattern,
        evidence: list[ComplaintEvidence],
        attempt: int,
        validation_errors: list[str] | None = None,
    ) -> LLMInvocationResult:
        self.call_count += 1
        self.last_validation_errors = validation_errors
        response: OpportunityLLMOutput | None = None

        topic_key = pattern.topic.lower()
        if topic_key in self._by_topic:
            response = self._by_topic[topic_key]
        elif self._index < len(self._responses):
            response = self._responses[self._index]
            self._index += 1

        if response is None:
            return LLMInvocationResult(
                parsed=None,
                raw_text="not valid json",
                model=self._model,
                error="no_more_mock_responses",
            )

        return LLMInvocationResult(
            parsed=response,
            raw_text=response.model_dump_json(),
            model=self._model,
            prompt_tokens=200,
            completion_tokens=120,
            latency_ms=15,
            cost_usd=0.0,
        )
