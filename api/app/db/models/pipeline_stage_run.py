"""Per-stage execution records within a pipeline run."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import PipelineStageStatus

if TYPE_CHECKING:
    from app.db.models.pipeline_run import PipelineRun


class PipelineStageRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "pipeline_stage_runs"

    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=PipelineStageStatus.PENDING.value,
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items_in: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    items_out: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    items_failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    pipeline_run: Mapped[PipelineRun] = relationship(back_populates="stage_runs")

    __table_args__ = (
        Index("idx_pipeline_stage_runs_pipeline", "pipeline_run_id", "sequence"),
        Index("idx_pipeline_stage_runs_stage", "pipeline_run_id", "stage"),
    )
