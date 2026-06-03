"""LLM call audit repository."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.llm_call import LLMCall
from app.repositories.base import BaseRepository


class LLMCallRepository(BaseRepository[LLMCall]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LLMCall)

    async def log_classification_attempt(
        self,
        *,
        signal_id: UUID,
        graph_name: str,
        model: str,
        attempt: int,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int | None,
        cost_usd: float | None,
        status: str,
        error_detail: str | None,
        eval_metadata: dict[str, Any],
    ) -> LLMCall:
        return await self.log_agent_call(
            entity_type="signal",
            entity_id=signal_id,
            graph_name=graph_name,
            model=model,
            attempt=attempt,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            status=status,
            error_detail=error_detail,
            eval_metadata=eval_metadata,
        )

    async def log_agent_call(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        graph_name: str,
        model: str,
        attempt: int,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int | None,
        cost_usd: float | None,
        status: str,
        error_detail: str | None,
        eval_metadata: dict[str, Any],
    ) -> LLMCall:
        entity = LLMCall(
            entity_type=entity_type,
            entity_id=entity_id,
            graph_name=graph_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            status=status,
            attempt=attempt,
            error_detail=error_detail,
            eval_metadata=eval_metadata,
        )
        return await self.add(entity)
