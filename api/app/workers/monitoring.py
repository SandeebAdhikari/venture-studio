"""Redis-backed job monitoring for ARQ workers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

from app.config import Settings, get_settings
from app.workers.schemas import JobRecord, JobStatus

RECENT_JOBS_KEY = "jobs:recent"
JOB_STATUS_PREFIX = "job:status:"


class JobMonitor:
    """Tracks job lifecycle in Redis for observability and debugging."""

    def __init__(self, redis: Redis, settings: Settings | None = None) -> None:
        self._redis = redis
        self._settings = settings or get_settings()

    def _key(self, job_id: str) -> str:
        return f"{JOB_STATUS_PREFIX}{job_id}"

    async def record_enqueued(
        self,
        *,
        job_id: str,
        job_name: str,
        kwargs: dict[str, Any] | None = None,
        max_tries: int = 3,
    ) -> JobRecord:
        now = datetime.now(UTC)
        record = JobRecord(
            job_id=job_id,
            job_name=job_name,
            status=JobStatus.QUEUED,
            max_tries=max_tries,
            enqueued_at=now,
            kwargs=kwargs or {},
        )
        await self._save(record)
        await self._redis.zadd(RECENT_JOBS_KEY, {job_id: now.timestamp()})
        return record

    async def record_started(
        self,
        *,
        job_id: str,
        job_name: str,
        attempt: int,
        max_tries: int,
        worker_id: str | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> JobRecord:
        existing = await self.get(job_id)
        now = datetime.now(UTC)
        record = existing or JobRecord(
            job_id=job_id,
            job_name=job_name,
            status=JobStatus.RUNNING,
            max_tries=max_tries,
            kwargs=kwargs or {},
        )
        record.status = JobStatus.RUNNING
        record.attempt = attempt
        record.max_tries = max_tries
        record.started_at = now
        record.worker_id = worker_id
        if kwargs:
            record.kwargs = kwargs
        await self._save(record)
        return record

    async def record_completed(
        self,
        *,
        job_id: str,
        result: dict[str, Any],
    ) -> JobRecord:
        record = await self._require(job_id)
        finished = datetime.now(UTC)
        record.status = JobStatus.COMPLETED
        record.finished_at = finished
        record.result = result
        record.error = None
        if record.started_at is not None:
            record.duration_ms = int((finished - record.started_at).total_seconds() * 1000)
        await self._save(record)
        return record

    async def record_failed(
        self,
        *,
        job_id: str,
        error: str,
        attempt: int,
        max_tries: int,
    ) -> JobRecord:
        record = await self._require(job_id)
        finished = datetime.now(UTC)
        record.attempt = attempt
        record.max_tries = max_tries
        record.error = error
        if attempt >= max_tries:
            record.status = JobStatus.FAILED
            record.finished_at = finished
            if record.started_at is not None:
                record.duration_ms = int((finished - record.started_at).total_seconds() * 1000)
        else:
            record.status = JobStatus.DEFERRED
        await self._save(record)
        return record

    async def get(self, job_id: str) -> JobRecord | None:
        raw = await self._redis.get(self._key(job_id))
        if raw is None:
            return None
        return JobRecord.model_validate_json(raw)

    async def list_recent(self, *, limit: int = 20) -> list[JobRecord]:
        job_ids = await self._redis.zrevrange(RECENT_JOBS_KEY, 0, limit - 1)
        records: list[JobRecord] = []
        for job_id in job_ids:
            record = await self.get(job_id)
            if record is not None:
                records.append(record)
        return records

    async def _require(self, job_id: str) -> JobRecord:
        record = await self.get(job_id)
        if record is None:
            return JobRecord(job_id=job_id, job_name="unknown", status=JobStatus.RUNNING)
        return record

    async def _save(self, record: JobRecord) -> None:
        await self._redis.set(
            self._key(record.job_id),
            record.model_dump_json(),
            ex=self._settings.arq_job_status_ttl_sec,
        )

    @staticmethod
    def parse_raw(raw: str | bytes | None) -> JobRecord | None:
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        return JobRecord.model_validate(json.loads(raw))
