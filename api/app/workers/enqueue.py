"""Enqueue ARQ jobs from the API layer."""

from __future__ import annotations

from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import Settings, get_settings
from app.db.enums import PipelineTrigger
from app.exceptions import ValidationError
from app.schemas.pipeline import PipelineRunOptions
from app.workers.jobs import STAGE_JOB_MAP
from app.workers.monitoring import JobMonitor
from app.workers.schemas import JobEnqueueResult, JobOptions

_pool: ArqRedis | None = None

REGISTERED_JOBS = frozenset({*STAGE_JOB_MAP.keys(), "run_pipeline"})


def get_redis_settings(settings: Settings | None = None) -> RedisSettings:
    settings = settings or get_settings()
    return RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        database=settings.redis_db,
        password=settings.redis_password,
    )


async def get_arq_pool(settings: Settings | None = None) -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(get_redis_settings(settings))
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


class JobEnqueuer:
    """Publishes background jobs to Redis for ARQ workers."""

    def __init__(self, redis: ArqRedis, settings: Settings | None = None) -> None:
        self._redis = redis
        self._settings = settings or get_settings()
        self._monitor = JobMonitor(redis, self._settings)

    async def enqueue(
        self,
        job_name: str,
        *,
        options: dict[str, Any] | None = None,
        _defer_by: int | None = None,
        **job_kwargs: Any,
    ) -> JobEnqueueResult:
        if job_name not in REGISTERED_JOBS:
            raise ValidationError(
                f"Unknown job '{job_name}'. Valid jobs: {sorted(REGISTERED_JOBS)}"
            )

        if job_name == "run_pipeline":
            enqueue_kwargs = {
                "trigger": job_kwargs.get("trigger", "api"),
                "options": job_kwargs.get("options") or options or {},
            }
        else:
            enqueue_kwargs = {"options": options or {}}

        job = await self._redis.enqueue_job(
            job_name,
            **enqueue_kwargs,
            _defer_by=_defer_by,
        )
        if job is None:
            raise ValidationError(f"Failed to enqueue job '{job_name}'")

        await self._monitor.record_enqueued(
            job_id=job.job_id,
            job_name=job_name,
            kwargs=enqueue_kwargs,
            max_tries=self._settings.arq_max_tries,
        )
        return JobEnqueueResult(job_id=job.job_id, job_name=job_name)

    async def enqueue_pipeline(
        self,
        *,
        trigger: PipelineTrigger = PipelineTrigger.API,
        options: PipelineRunOptions | None = None,
    ) -> JobEnqueueResult:
        return await self.enqueue(
            "run_pipeline",
            trigger=trigger.value,
            options=(options or PipelineRunOptions()).model_dump(mode="json"),
        )

    async def enqueue_stage(
        self,
        job_name: str,
        *,
        options: JobOptions | None = None,
    ) -> JobEnqueueResult:
        payload = (options or JobOptions()).model_dump(mode="json", exclude_none=True)
        return await self.enqueue(job_name, options=payload)

    async def get_job(self, job_id: str):
        return await self._monitor.get(job_id)

    async def list_recent_jobs(self, *, limit: int = 20):
        return await self._monitor.list_recent(limit=limit)
