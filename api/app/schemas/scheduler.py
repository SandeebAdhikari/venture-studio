"""Scheduler API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import SchedulerRunStatus, SchedulerTrigger
from app.schemas.common import UUIDSchema


class SchedulerRunRead(UUIDSchema):
    model_config = ConfigDict(from_attributes=True)

    job_name: str
    trigger: SchedulerTrigger
    status: SchedulerRunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    error: str | None = None
    arq_job_ids: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict, validation_alias="metadata_")


class SchedulerJobRead(UUIDSchema):
    job_name: str
    display_name: str
    description: str | None = None
    schedule_hour: int
    schedule_minute: int
    enabled: bool
    schedule_cron: str
    last_run: SchedulerRunRead | None = None
    failure_count: int = 0


class SchedulerJobUpdate(BaseModel):
    enabled: bool


class SchedulerRunResult(BaseModel):
    run_id: UUID
    job_name: str
    status: SchedulerRunStatus
    arq_job_ids: list[str] = Field(default_factory=list)
