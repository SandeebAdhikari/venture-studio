"""Background job schemas."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.enums import PipelineTrigger
from app.schemas.pipeline import PipelineRunOptions


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DEFERRED = "deferred"


class JobOptions(BaseModel):
    """Options passed to individual stage jobs."""

    force: bool = False
    founder_profile_id: UUID | None = None
    top_n: int | None = Field(default=None, ge=1, le=50)
    classify_batch_size: int | None = Field(default=None, ge=1)
    classify_max_batches: int | None = Field(default=None, ge=1)
    score_limit: int | None = Field(default=None, ge=1)
    idempotency_key: str | None = Field(
        default=None,
        description="When set, concurrent jobs with the same key are skipped.",
    )


class JobRecord(BaseModel):
    job_id: str
    job_name: str
    status: JobStatus
    attempt: int = 1
    max_tries: int = 3
    enqueued_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    worker_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    kwargs: dict[str, Any] = Field(default_factory=dict)


class JobEnqueueResult(BaseModel):
    job_id: str
    job_name: str
    status: JobStatus = JobStatus.QUEUED


class RunPipelineJobRequest(BaseModel):
    trigger: PipelineTrigger = PipelineTrigger.API
    options: PipelineRunOptions = Field(default_factory=PipelineRunOptions)


class RunStageJobRequest(BaseModel):
    options: JobOptions = Field(default_factory=JobOptions)
