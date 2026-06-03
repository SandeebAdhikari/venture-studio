"""Scheduler run history."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.scheduler_job import SchedulerJob


class SchedulerRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scheduler_runs"

    job_name: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("scheduler_jobs.job_name", ondelete="CASCADE"),
        nullable=False,
    )
    trigger: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    arq_job_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")

    job: Mapped[SchedulerJob] = relationship(back_populates="runs")

    __table_args__ = (
        Index("idx_scheduler_runs_job_name", "job_name"),
        Index("idx_scheduler_runs_status", "status"),
        Index("idx_scheduler_runs_started_at", "started_at"),
    )
