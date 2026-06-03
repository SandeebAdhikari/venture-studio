"""Pipeline run repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import PipelineRunStatus, PipelineStageStatus
from app.db.models.pipeline_run import PipelineRun
from app.db.models.pipeline_stage_run import PipelineStageRun
from app.repositories.base import BaseRepository
from app.schemas.pipeline import PipelineRunCreate, PipelineStageRunCreate


class PipelineRepository(BaseRepository[PipelineRun]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PipelineRun)

    async def get_running(self) -> PipelineRun | None:
        result = await self.session.execute(
            select(PipelineRun).where(PipelineRun.status == PipelineRunStatus.RUNNING.value)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_stages(self, run_id: UUID) -> PipelineRun | None:
        result = await self.session.execute(
            select(PipelineRun)
            .options(selectinload(PipelineRun.stage_runs))
            .where(PipelineRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def list_runs(self, *, limit: int = 20, offset: int = 0) -> list[PipelineRun]:
        result = await self.session.execute(
            select(PipelineRun)
            .order_by(PipelineRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_runs(self) -> int:
        result = await self.session.scalar(select(func.count()).select_from(PipelineRun))
        return int(result or 0)

    async def create_run(self, data: PipelineRunCreate) -> PipelineRun:
        entity = PipelineRun(
            trigger=data.trigger.value,
            status=PipelineRunStatus.PENDING.value,
            founder_profile_id=data.founder_profile_id,
            config_snapshot=data.config_snapshot,
            audit_trail=[],
        )
        return await self.add(entity)

    async def create_stage_runs(
        self,
        pipeline_run_id: UUID,
        stages: list[PipelineStageRunCreate],
    ) -> list[PipelineStageRun]:
        entities: list[PipelineStageRun] = []
        for stage in stages:
            entity = PipelineStageRun(
                pipeline_run_id=pipeline_run_id,
                stage=stage.stage.value,
                sequence=stage.sequence,
                status=PipelineStageStatus.PENDING.value,
                max_attempts=stage.max_attempts,
            )
            self.session.add(entity)
            entities.append(entity)
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities

    async def append_audit_event(
        self,
        run: PipelineRun,
        event: dict[str, Any],
    ) -> PipelineRun:
        trail = list(run.audit_trail or [])
        trail.append({**event, "timestamp": datetime.now(UTC).isoformat()})
        run.audit_trail = trail
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def mark_run_started(self, run: PipelineRun) -> PipelineRun:
        run.status = PipelineRunStatus.RUNNING.value
        run.started_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def mark_run_finished(
        self,
        run: PipelineRun,
        *,
        status: PipelineRunStatus,
        error_summary: str | None = None,
    ) -> PipelineRun:
        finished_at = datetime.now(UTC)
        run.status = status.value
        run.finished_at = finished_at
        run.error_summary = error_summary
        if run.started_at is not None:
            run.duration_ms = int((finished_at - run.started_at).total_seconds() * 1000)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def update_run_counters(
        self,
        run: PipelineRun,
        *,
        stages_completed: int,
        stages_failed: int,
        stages_skipped: int,
    ) -> PipelineRun:
        run.stages_completed = stages_completed
        run.stages_failed = stages_failed
        run.stages_skipped = stages_skipped
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_stage_run(
        self,
        pipeline_run_id: UUID,
        stage: str,
    ) -> PipelineStageRun | None:
        result = await self.session.execute(
            select(PipelineStageRun).where(
                PipelineStageRun.pipeline_run_id == pipeline_run_id,
                PipelineStageRun.stage == stage,
            )
        )
        return result.scalar_one_or_none()

    async def mark_stage_started(self, stage_run: PipelineStageRun) -> PipelineStageRun:
        stage_run.status = PipelineStageStatus.RUNNING.value
        stage_run.started_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(stage_run)
        return stage_run

    async def mark_stage_retrying(self, stage_run: PipelineStageRun) -> PipelineStageRun:
        stage_run.status = PipelineStageStatus.RETRYING.value
        stage_run.attempt += 1
        await self.session.flush()
        await self.session.refresh(stage_run)
        return stage_run

    async def mark_stage_skipped(
        self,
        stage_run: PipelineStageRun,
        *,
        reason: str,
    ) -> PipelineStageRun:
        finished_at = datetime.now(UTC)
        stage_run.status = PipelineStageStatus.SKIPPED.value
        stage_run.finished_at = finished_at
        if stage_run.started_at is not None:
            stage_run.duration_ms = int((finished_at - stage_run.started_at).total_seconds() * 1000)
        stage_run.stage_metadata = {**stage_run.stage_metadata, "skip_reason": reason}
        await self.session.flush()
        await self.session.refresh(stage_run)
        return stage_run

    async def mark_stage_completed(
        self,
        stage_run: PipelineStageRun,
        *,
        items_in: int,
        items_out: int,
        items_failed: int,
        records_processed: int,
        stage_metadata: dict[str, Any] | None = None,
    ) -> PipelineStageRun:
        finished_at = datetime.now(UTC)
        stage_run.status = PipelineStageStatus.COMPLETED.value
        stage_run.finished_at = finished_at
        stage_run.items_in = items_in
        stage_run.items_out = items_out
        stage_run.items_failed = items_failed
        stage_run.records_processed = records_processed
        if stage_metadata:
            stage_run.stage_metadata = {**stage_run.stage_metadata, **stage_metadata}
        if stage_run.started_at is not None:
            stage_run.duration_ms = int((finished_at - stage_run.started_at).total_seconds() * 1000)
        await self.session.flush()
        await self.session.refresh(stage_run)
        return stage_run

    async def mark_stage_failed(
        self,
        stage_run: PipelineStageRun,
        *,
        error_detail: str,
        items_in: int = 0,
        items_out: int = 0,
        items_failed: int = 0,
        records_processed: int = 0,
    ) -> PipelineStageRun:
        finished_at = datetime.now(UTC)
        stage_run.status = PipelineStageStatus.FAILED.value
        stage_run.finished_at = finished_at
        stage_run.error_detail = error_detail
        stage_run.items_in = items_in
        stage_run.items_out = items_out
        stage_run.items_failed = items_failed
        stage_run.records_processed = records_processed
        if stage_run.started_at is not None:
            stage_run.duration_ms = int((finished_at - stage_run.started_at).total_seconds() * 1000)
        await self.session.flush()
        await self.session.refresh(stage_run)
        return stage_run

    async def cancel_stale_running_runs(self) -> int:
        result = await self.session.execute(
            update(PipelineRun)
            .where(PipelineRun.status == PipelineRunStatus.RUNNING.value)
            .values(
                status=PipelineRunStatus.FAILED.value,
                error_summary="Run marked failed during recovery",
                finished_at=datetime.now(UTC),
            )
        )
        return int(result.rowcount or 0)
