"""Pipeline persistence and API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.enums import (
    PipelineRunStatus,
    PipelineStage,
    PipelineStageStatus,
    PipelineTrigger,
)
from app.db.models.pipeline_run import PipelineRun
from app.db.models.pipeline_stage_run import PipelineStageRun


class PipelineRunCreate(BaseModel):
    trigger: PipelineTrigger = PipelineTrigger.API
    founder_profile_id: UUID | None = None
    config_snapshot: dict[str, Any] = Field(default_factory=dict)


class PipelineStageRunCreate(BaseModel):
    stage: PipelineStage
    sequence: int = Field(ge=1)
    max_attempts: int = Field(default=3, ge=1)


class PipelineRunOptions(BaseModel):
    """Runtime options for a pipeline execution."""

    skip_stages: list[PipelineStage] = Field(default_factory=list)
    stages_only: list[PipelineStage] | None = None
    stop_on_failure: bool = True
    max_retries: int | None = Field(default=None, ge=0, le=10)
    force: bool = False
    founder_profile_id: UUID | None = None
    top_n: int | None = Field(default=None, ge=1, le=50)
    classify_batch_size: int | None = Field(default=None, ge=1)
    classify_max_batches: int | None = Field(default=None, ge=1)
    score_limit: int | None = Field(default=None, ge=1)
    discovery_validation_mode: bool = False
    founder_signal_neighborhood: str | None = Field(
        default=None,
        description="Neighborhood for classification prompt routing (stripe_billing, security, …)",
    )
    pipeline_run_id: UUID | None = Field(
        default=None,
        description="Set by orchestrator; stored in ranking_metadata and report_metadata",
    )
    validation_ranking_run_id: UUID | None = Field(
        default=None,
        description="Executive ranking run produced in the current pipeline run",
    )


class PipelineStageRunRead(BaseModel):
    id: UUID
    stage: PipelineStage
    sequence: int
    status: PipelineStageStatus
    attempt: int
    max_attempts: int
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    items_in: int
    items_out: int
    items_failed: int
    records_processed: int
    error_detail: str | None
    stage_metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: PipelineStageRun) -> PipelineStageRunRead:
        return cls(
            id=entity.id,
            stage=PipelineStage(entity.stage),
            sequence=entity.sequence,
            status=PipelineStageStatus(entity.status),
            attempt=entity.attempt,
            max_attempts=entity.max_attempts,
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            duration_ms=entity.duration_ms,
            items_in=entity.items_in,
            items_out=entity.items_out,
            items_failed=entity.items_failed,
            records_processed=entity.records_processed,
            error_detail=entity.error_detail,
            stage_metadata=entity.stage_metadata,
        )


class PipelineRunRead(BaseModel):
    id: UUID
    trigger: PipelineTrigger
    status: PipelineRunStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    founder_profile_id: UUID | None
    config_snapshot: dict[str, Any]
    error_summary: str | None
    stages_completed: int
    stages_failed: int
    stages_skipped: int
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: PipelineRun) -> PipelineRunRead:
        return cls(
            id=entity.id,
            trigger=PipelineTrigger(entity.trigger),
            status=PipelineRunStatus(entity.status),
            started_at=entity.started_at,
            finished_at=entity.finished_at,
            duration_ms=entity.duration_ms,
            founder_profile_id=entity.founder_profile_id,
            config_snapshot=entity.config_snapshot,
            error_summary=entity.error_summary,
            stages_completed=entity.stages_completed,
            stages_failed=entity.stages_failed,
            stages_skipped=entity.stages_skipped,
            created_at=entity.created_at,
        )


class PipelineRunDetail(PipelineRunRead):
    audit_trail: list[dict[str, Any]]
    stage_runs: list[PipelineStageRunRead]

    @classmethod
    def from_entity(cls, entity: PipelineRun) -> PipelineRunDetail:
        base = PipelineRunRead.from_entity(entity)
        return cls(
            **base.model_dump(),
            audit_trail=entity.audit_trail or [],
            stage_runs=[PipelineStageRunRead.from_entity(stage) for stage in entity.stage_runs],
        )


class PipelineRunRequest(BaseModel):
    trigger: PipelineTrigger = PipelineTrigger.API
    options: PipelineRunOptions = Field(default_factory=PipelineRunOptions)


class PipelineRunResult(BaseModel):
    pipeline_run_id: UUID
    status: PipelineRunStatus
    stages_completed: int
    stages_failed: int
    stages_skipped: int
    duration_ms: int | None
