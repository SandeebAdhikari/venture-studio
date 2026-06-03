"""Scheduler job configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.scheduler_run import SchedulerRun


class SchedulerJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scheduler_jobs"

    job_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schedule_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    schedule_minute: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    runs: Mapped[list[SchedulerRun]] = relationship(back_populates="job")

    __table_args__ = (
        CheckConstraint("schedule_hour >= 0 AND schedule_hour <= 23", name="ck_scheduler_jobs_hour"),
        CheckConstraint(
            "schedule_minute >= 0 AND schedule_minute <= 59",
            name="ck_scheduler_jobs_minute",
        ),
        Index("idx_scheduler_jobs_enabled", "enabled"),
    )
