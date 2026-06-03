"""Scheduler management service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.exceptions import ValidationError
from app.repositories import RepositoryContainer
from app.scheduler.definitions import SCHEDULER_JOB_MAP
from app.scheduler.scheduler import get_scheduler
from app.schemas.scheduler import SchedulerJobRead, SchedulerJobUpdate, SchedulerRunRead, SchedulerRunResult

if TYPE_CHECKING:
    from app.workers.enqueue import JobEnqueuer


class SchedulerService:
    def __init__(self, repos: RepositoryContainer) -> None:
        self._repos = repos

    async def list_jobs(self) -> list[SchedulerJobRead]:
        await self._repos.scheduler_jobs.ensure_defaults()
        jobs = await self._repos.scheduler_jobs.list_all()
        items: list[SchedulerJobRead] = []
        for job in jobs:
            last_run = await self._repos.scheduler_runs.get_latest_for_job(job.job_name)
            failure_count = await self._repos.scheduler_runs.count_failures_for_job(job.job_name)
            items.append(
                SchedulerJobRead(
                    id=job.id,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                    job_name=job.job_name,
                    display_name=job.display_name,
                    description=job.description,
                    schedule_hour=job.schedule_hour,
                    schedule_minute=job.schedule_minute,
                    enabled=job.enabled,
                    schedule_cron=self._format_cron(job.schedule_hour, job.schedule_minute),
                    last_run=SchedulerRunRead.model_validate(last_run) if last_run else None,
                    failure_count=failure_count,
                )
            )
        return items

    async def update_job(self, job_name: str, data: SchedulerJobUpdate) -> SchedulerJobRead:
        if job_name not in SCHEDULER_JOB_MAP:
            raise ValidationError(f"Unknown scheduler job '{job_name}'")

        await self._repos.scheduler_jobs.ensure_defaults()
        job = await self._repos.scheduler_jobs.get_by_name(job_name)
        if job is None:
            raise ValidationError(f"Scheduler job '{job_name}' is not configured")

        job = await self._repos.scheduler_jobs.set_enabled(job, data.enabled)
        scheduler = get_scheduler()
        await scheduler.sync_job(
            job.job_name,
            enabled=job.enabled,
            hour=job.schedule_hour,
            minute=job.schedule_minute,
        )

        last_run = await self._repos.scheduler_runs.get_latest_for_job(job.job_name)
        failure_count = await self._repos.scheduler_runs.count_failures_for_job(job.job_name)
        return SchedulerJobRead(
            id=job.id,
            created_at=job.created_at,
            updated_at=job.updated_at,
            job_name=job.job_name,
            display_name=job.display_name,
            description=job.description,
            schedule_hour=job.schedule_hour,
            schedule_minute=job.schedule_minute,
            enabled=job.enabled,
            schedule_cron=self._format_cron(job.schedule_hour, job.schedule_minute),
            last_run=SchedulerRunRead.model_validate(last_run) if last_run else None,
            failure_count=failure_count,
        )

    async def trigger_job(self, job_name: str, enqueuer: JobEnqueuer) -> SchedulerRunResult:
        if job_name not in SCHEDULER_JOB_MAP:
            raise ValidationError(
                f"Unknown scheduler job '{job_name}'. Valid jobs: {sorted(SCHEDULER_JOB_MAP.keys())}"
            )

        await self._repos.scheduler_jobs.ensure_defaults()
        job = await self._repos.scheduler_jobs.get_by_name(job_name)
        if job is None:
            raise ValidationError(f"Scheduler job '{job_name}' is not configured")
        if not job.enabled:
            raise ValidationError(f"Scheduler job '{job_name}' is disabled")

        from app.db.enums import SchedulerRunStatus, SchedulerTrigger
        from app.scheduler.jobs import execute_scheduler_job

        run_id = await execute_scheduler_job(
            job_name,
            trigger=SchedulerTrigger.MANUAL,
            repos=self._repos,
            enqueuer=enqueuer,
        )
        run = await self._repos.scheduler_runs.get_by_id(run_id)
        assert run is not None
        return SchedulerRunResult(
            run_id=run.id,
            job_name=run.job_name,
            status=SchedulerRunStatus(run.status),
            arq_job_ids=run.arq_job_ids,
        )

    @staticmethod
    def _format_cron(hour: int, minute: int) -> str:
        return f"{minute} {hour} * * *"
