"""APScheduler integration for automated Venture Studio runs."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings, get_settings
from app.db.session import get_session_factory
from app.logging import get_logger
from app.repositories import get_repositories
from app.scheduler.jobs import run_scheduled_job

logger = get_logger(__name__)

_scheduler: VentureStudioScheduler | None = None


class VentureStudioScheduler:
    """Manages cron schedules that enqueue ARQ pipeline jobs."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        timezone = ZoneInfo(self._settings.scheduler_timezone)
        self._scheduler = AsyncIOScheduler(timezone=timezone)
        self._started = False

    @property
    def is_running(self) -> bool:
        return self._started and self._scheduler.running

    async def start(self) -> None:
        if not self._settings.scheduler_enabled:
            logger.info("Scheduler disabled via configuration")
            return
        if self._started:
            return

        factory = get_session_factory()
        async with factory() as session:
            repos = get_repositories(session)
            await repos.scheduler_jobs.ensure_defaults()
            jobs = await repos.scheduler_jobs.list_enabled()
            await session.commit()

        for job in jobs:
            self._register_job(job.job_name, job.schedule_hour, job.schedule_minute)

        self._scheduler.start()
        self._started = True
        logger.info(
            "Scheduler started",
            extra={
                "timezone": self._settings.scheduler_timezone,
                "jobs_registered": len(jobs),
            },
        )

    async def shutdown(self) -> None:
        if not self._started:
            return
        self._scheduler.shutdown(wait=False)
        self._started = False
        logger.info("Scheduler stopped")

    def _register_job(self, job_name: str, hour: int, minute: int) -> None:
        self._scheduler.add_job(
            run_scheduled_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=job_name,
            name=job_name,
            args=[job_name],
            replace_existing=True,
            misfire_grace_time=3600,
            coalesce=True,
            max_instances=1,
        )
        logger.info(
            "Registered scheduler job",
            extra={"job_name": job_name, "hour": hour, "minute": minute},
        )

    def _remove_job(self, job_name: str) -> None:
        if self._scheduler.get_job(job_name) is not None:
            self._scheduler.remove_job(job_name)

    async def sync_job(self, job_name: str, *, enabled: bool, hour: int, minute: int) -> None:
        """Apply enable/disable or schedule changes to APScheduler."""
        if not self._started:
            return
        self._remove_job(job_name)
        if enabled:
            self._register_job(job_name, hour, minute)


def get_scheduler() -> VentureStudioScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = VentureStudioScheduler(get_settings())
    return _scheduler


async def start_scheduler() -> VentureStudioScheduler:
    scheduler = get_scheduler()
    await scheduler.start()
    return scheduler


async def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        await _scheduler.shutdown()
        _scheduler = None


async def reset_scheduler_for_tests() -> None:
    """Stop and clear the global scheduler singleton (tests only)."""
    await shutdown_scheduler()
