"""Scheduler job repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.scheduler_job import SchedulerJob
from app.repositories.base import BaseRepository
from app.scheduler.definitions import DEFAULT_SCHEDULER_JOBS, SchedulerJobDefinition


class SchedulerJobRepository(BaseRepository[SchedulerJob]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SchedulerJob)

    async def get_by_name(self, job_name: str) -> SchedulerJob | None:
        result = await self.session.execute(
            select(SchedulerJob).where(SchedulerJob.job_name == job_name)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[SchedulerJob]:
        result = await self.session.execute(
            select(SchedulerJob).order_by(SchedulerJob.schedule_hour, SchedulerJob.schedule_minute)
        )
        return list(result.scalars().all())

    async def list_enabled(self) -> list[SchedulerJob]:
        result = await self.session.execute(
            select(SchedulerJob)
            .where(SchedulerJob.enabled.is_(True))
            .order_by(SchedulerJob.schedule_hour, SchedulerJob.schedule_minute)
        )
        return list(result.scalars().all())

    async def create_from_definition(self, definition: SchedulerJobDefinition) -> SchedulerJob:
        entity = SchedulerJob(
            job_name=definition.job_name,
            display_name=definition.display_name,
            description=definition.description,
            schedule_hour=definition.schedule_hour,
            schedule_minute=definition.schedule_minute,
            enabled=True,
        )
        return await self.add(entity)

    async def ensure_defaults(self) -> None:
        for definition in DEFAULT_SCHEDULER_JOBS:
            existing = await self.get_by_name(definition.job_name)
            if existing is None:
                await self.create_from_definition(definition)
                continue

            existing.display_name = definition.display_name
            existing.description = definition.description
            existing.schedule_hour = definition.schedule_hour
            existing.schedule_minute = definition.schedule_minute
            await self.session.flush()
            await self.session.refresh(existing)

    async def set_enabled(self, entity: SchedulerJob, enabled: bool) -> SchedulerJob:
        entity.enabled = enabled
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
