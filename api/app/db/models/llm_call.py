"""LLM audit log for classification and future agents."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LLMCall(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "llm_calls"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    graph_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="success")
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    eval_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    __table_args__ = (
        Index("idx_llm_calls_entity", "entity_type", "entity_id"),
        Index("idx_llm_calls_created", "created_at"),
        Index("idx_llm_calls_graph_status", "graph_name", "status"),
    )
