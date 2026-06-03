"""Scheduler job execution handlers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from app.db.enums import PipelineTrigger, SchedulerRunStatus, SchedulerTrigger
from app.logging import get_logger
from app.scheduler.definitions import PIPELINE_ARQ_JOB, get_job_definition
from app.schemas.pipeline import PipelineRunOptions

if TYPE_CHECKING:
    from app.repositories import RepositoryContainer
    from app.workers.enqueue import JobEnqueuer

logger = get_logger(__name__)


async def _enqueue_orchestrated_pipeline(
    *,
    job_name: str,
    idempotency_key: str,
    enqueuer: JobEnqueuer,
) -> tuple[list[str], dict[str, Any]]:
    result = await enqueuer.enqueue_pipeline(
        trigger=PipelineTrigger.SCHEDULED,
        options=PipelineRunOptions(),
        idempotency_key=idempotency_key,
    )
    metadata = {
        "execution_mode": "orchestrator",
        "arq_jobs": [PIPELINE_ARQ_JOB],
        "pipeline_trigger": PipelineTrigger.SCHEDULED.value,
    }
    logger.info(
        "Scheduler enqueued orchestrated pipeline",
        extra={"scheduler_job": job_name, "arq_job_id": result.job_id},
    )
    return [result.job_id], metadata


async def _enqueue_stage_jobs(
    *,
    job_name: str,
    arq_jobs: tuple[str, ...],
    idempotency_key: str,
    enqueuer: JobEnqueuer,
) -> tuple[list[str], list[str], dict[str, Any]]:
    from app.workers.schemas import JobOptions

    arq_job_ids: list[str] = []
    errors: list[str] = []

    for arq_job_name in arq_jobs:
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

    metadata: dict[str, Any] = {
        "execution_mode": "stage_jobs",
        "arq_jobs": list(arq_jobs),
        "enqueued_count": len(arq_job_ids),
        "failed_count": len(errors),
    }
    return arq_job_ids, errors, metadata


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

    try:
        if definition.is_orchestrated:
            arq_job_ids, metadata = await _enqueue_orchestrated_pipeline(
                job_name=job_name,
                idempotency_key=idempotency_key,
                enqueuer=enqueuer,
            )
        else:
            arq_job_ids, errors, metadata = await _enqueue_stage_jobs(
                job_name=job_name,
                arq_jobs=definition.arq_jobs,
                idempotency_key=idempotency_key,
                enqueuer=enqueuer,
            )

        finished = datetime.now(UTC)

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
                "execution_mode": metadata.get("execution_mode"),
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
