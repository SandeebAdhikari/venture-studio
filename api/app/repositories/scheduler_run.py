"""Scheduler run history repository."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import SchedulerRunStatus, SchedulerTrigger
from app.db.models.scheduler_run import SchedulerRun
from app.repositories.base import BaseRepository


class SchedulerRunRepository(BaseRepository[SchedulerRun]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SchedulerRun)

    async def create_run(
        self,
        *,
        job_name: str,
        trigger: SchedulerTrigger,
    ) -> SchedulerRun:
        entity = SchedulerRun(
            job_name=job_name,
            trigger=trigger.value,
            status=SchedulerRunStatus.PENDING.value,
        )
        return await self.add(entity)

    async def mark_running(self, entity: SchedulerRun, *, started_at: datetime) -> SchedulerRun:
        entity.status = SchedulerRunStatus.RUNNING.value
        entity.started_at = started_at
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def mark_completed(
        self,
        entity: SchedulerRun,
        *,
        finished_at: datetime,
        arq_job_ids: list[str],
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> SchedulerRun:
        entity.status = SchedulerRunStatus.COMPLETED.value
        entity.finished_at = finished_at
        entity.arq_job_ids = arq_job_ids
        entity.error = error
        if metadata:
            entity.metadata_ = metadata
        if entity.started_at is not None:
            entity.duration_ms = int((finished_at - entity.started_at).total_seconds() * 1000)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def mark_failed(
        self,
        entity: SchedulerRun,
        *,
        error: str,
        finished_at: datetime | None = None,
        arq_job_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SchedulerRun:
        finished = finished_at or datetime.now(UTC)
        entity.status = SchedulerRunStatus.FAILED.value
        entity.finished_at = finished
        entity.error = error
        if arq_job_ids is not None:
            entity.arq_job_ids = arq_job_ids
        if metadata:
            entity.metadata_ = metadata
        if entity.started_at is not None:
            entity.duration_ms = int((finished - entity.started_at).total_seconds() * 1000)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get_latest_for_job(self, job_name: str) -> SchedulerRun | None:
        result = await self.session.execute(
            select(SchedulerRun)
            .where(SchedulerRun.job_name == job_name)
            .order_by(SchedulerRun.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_job(
        self,
        job_name: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SchedulerRun]:
        result = await self.session.execute(
            select(SchedulerRun)
            .where(SchedulerRun.job_name == job_name)
            .order_by(SchedulerRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_for_job(self, job_name: str) -> int:
        result = await self.session.scalar(
            select(func.count()).select_from(SchedulerRun).where(SchedulerRun.job_name == job_name)
        )
        return int(result or 0)

    async def count_failures_for_job(self, job_name: str) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(SchedulerRun)
            .where(
                SchedulerRun.job_name == job_name,
                SchedulerRun.status == SchedulerRunStatus.FAILED.value,
            )
        )
        return int(result or 0)
