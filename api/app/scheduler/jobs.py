"""Scheduler job execution handlers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.db.enums import SchedulerRunStatus, SchedulerTrigger
from app.logging import get_logger
from app.scheduler.definitions import get_job_definition

if TYPE_CHECKING:
    from app.repositories import RepositoryContainer
    from app.workers.enqueue import JobEnqueuer

logger = get_logger(__name__)


async def execute_scheduler_job(
    job_name: str,
    *,
    trigger: SchedulerTrigger,
    repos: RepositoryContainer,
    enqueuer: JobEnqueuer,
) -> UUID:
    """Enqueue ARQ work for a scheduler job and persist run history."""
    definition = get_job_definition(job_name)
    if definition is None:
        raise ValueError(f"Unknown scheduler job '{job_name}'")

    job = await repos.scheduler_jobs.get_by_name(job_name)
    if job is None:
        raise ValueError(f"Scheduler job '{job_name}' is not configured")
    if not job.enabled and trigger == SchedulerTrigger.SCHEDULED:
        raise RuntimeError(f"Scheduler job '{job_name}' is disabled")

    run = await repos.scheduler_runs.create_run(job_name=job_name, trigger=trigger)
    started = datetime.now(UTC)
    await repos.scheduler_runs.mark_running(run, started_at=started)

    arq_job_ids: list[str] = []
    errors: list[str] = []

    idempotency_key = f"scheduler:{job_name}:{date.today().isoformat()}"

    from app.workers.schemas import JobOptions

    try:
        for arq_job_name in definition.arq_jobs:
            try:
                result = await enqueuer.enqueue_stage(
                    arq_job_name,
                    options=JobOptions(idempotency_key=f"{idempotency_key}:{arq_job_name}"),
                )
                arq_job_ids.append(result.job_id)
            except Exception as exc:
                errors.append(f"{arq_job_name}: {exc}")
                logger.exception(
                    "Failed to enqueue ARQ job from scheduler",
                    extra={"scheduler_job": job_name, "arq_job": arq_job_name},
                )

        finished = datetime.now(UTC)
        metadata: dict[str, Any] = {
            "arq_jobs": list(definition.arq_jobs),
            "enqueued_count": len(arq_job_ids),
            "failed_count": len(errors),
        }

        if errors and not arq_job_ids:
            await repos.scheduler_runs.mark_failed(
                run,
                error="; ".join(errors),
                finished_at=finished,
                arq_job_ids=arq_job_ids,
                metadata=metadata,
            )
            raise RuntimeError(f"Scheduler job '{job_name}' failed: {'; '.join(errors)}")

        if errors:
            metadata["partial_errors"] = errors
            await repos.scheduler_runs.mark_completed(
                run,
                finished_at=finished,
                arq_job_ids=arq_job_ids,
                metadata=metadata,
                error=f"Partial enqueue failures: {'; '.join(errors)}",
            )
        else:
            await repos.scheduler_runs.mark_completed(
                run,
                finished_at=finished,
                arq_job_ids=arq_job_ids,
                metadata=metadata,
            )

        logger.info(
            "Scheduler job executed",
            extra={
                "scheduler_job": job_name,
                "trigger": trigger.value,
                "run_id": str(run.id),
                "arq_job_ids": arq_job_ids,
            },
        )
        return run.id
    except Exception as exc:
        if run.status == SchedulerRunStatus.RUNNING.value:
            await repos.scheduler_runs.mark_failed(
                run,
                error=str(exc),
                finished_at=datetime.now(UTC),
                arq_job_ids=arq_job_ids,
            )
        raise


async def run_scheduled_job(job_name: str) -> None:
    """APScheduler entrypoint — opens its own DB session and enqueuer."""
    from app.config import get_settings
    from app.db.session import get_session_factory
    from app.repositories import get_repositories
    from app.workers.enqueue import JobEnqueuer, get_arq_pool

    settings = get_settings()
    factory = get_session_factory()
    pool = await get_arq_pool(settings)
    enqueuer = JobEnqueuer(pool, settings)

    async with factory() as session:
        repos = get_repositories(session)
        try:
            await repos.scheduler_jobs.ensure_defaults()
            await execute_scheduler_job(
                job_name,
                trigger=SchedulerTrigger.SCHEDULED,
                repos=repos,
                enqueuer=enqueuer,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
