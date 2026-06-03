"""Top-level pipeline execution records."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import PipelineRunStatus, PipelineTrigger

if TYPE_CHECKING:
    from app.db.models.pipeline_stage_run import PipelineStageRun


class PipelineRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "pipeline_runs"

    trigger: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=PipelineRunStatus.PENDING.value,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    founder_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("founder_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_trail: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    stages_completed: Mapped[int] = mapped_column(nullable=False, server_default="0")
    stages_failed: Mapped[int] = mapped_column(nullable=False, server_default="0")
    stages_skipped: Mapped[int] = mapped_column(nullable=False, server_default="0")

    stage_runs: Mapped[list[PipelineStageRun]] = relationship(
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
        order_by="PipelineStageRun.sequence",
    )

    __table_args__ = (
        Index("idx_pipeline_runs_status_started", "status", "started_at"),
        Index("idx_pipeline_runs_created", "created_at"),
    )
