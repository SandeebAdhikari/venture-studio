"""Tests for ARQ worker configuration and job monitoring."""

import pytest
from redis.asyncio import Redis

from app.config import Settings
from app.workers.jobs import STAGE_JOB_MAP
from app.workers.monitoring import JobMonitor
from app.workers.schemas import JobStatus
from app.workers.worker import WorkerSettings


def test_worker_settings_registers_all_stage_jobs():
    job_names = {func.name for func in WorkerSettings.functions}
    expected = set(STAGE_JOB_MAP.keys()) | {"run_pipeline"}
    assert expected == job_names


def test_worker_settings_retry_and_timeout():
    settings = Settings(api_key="test-worker-settings-key")
    assert WorkerSettings.max_jobs == settings.arq_max_jobs
    assert WorkerSettings.job_timeout == settings.arq_job_timeout_sec
    for func in WorkerSettings.functions:
        assert func.max_tries == settings.arq_max_tries
        assert func.timeout_s == settings.arq_job_timeout_sec


@pytest.mark.asyncio
async def test_job_monitor_lifecycle():
    settings = Settings(api_key="test-monitor-key", arq_job_status_ttl_sec=60)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    monitor = JobMonitor(redis, settings)

    try:
        await monitor.record_enqueued(
            job_id="job-test-1",
            job_name="collect",
            kwargs={"options": {}},
            max_tries=3,
        )
        await monitor.record_started(
            job_id="job-test-1",
            job_name="collect",
            attempt=1,
            max_tries=3,
            worker_id="worker-a",
        )
        await monitor.record_completed(
            job_id="job-test-1",
            result={"status": "completed", "items_out": 2},
        )

        record = await monitor.get("job-test-1")
        assert record is not None
        assert record.status == JobStatus.COMPLETED
        assert record.result == {"status": "completed", "items_out": 2}
        assert record.worker_id == "worker-a"

        recent = await monitor.list_recent(limit=5)
        assert any(item.job_id == "job-test-1" for item in recent)
    finally:
        await redis.delete("job:status:job-test-1")
        await redis.zrem("jobs:recent", "job-test-1")
        await redis.aclose()


@pytest.mark.asyncio
async def test_job_monitor_records_failure_and_deferred():
    settings = Settings(api_key="test-monitor-fail-key", arq_job_status_ttl_sec=60)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    monitor = JobMonitor(redis, settings)

    try:
        await monitor.record_enqueued(job_id="job-test-2", job_name="classify", max_tries=3)
        await monitor.record_started(
            job_id="job-test-2",
            job_name="classify",
            attempt=1,
            max_tries=3,
        )
        await monitor.record_failed(
            job_id="job-test-2",
            error="transient",
            attempt=1,
            max_tries=3,
        )
        deferred = await monitor.get("job-test-2")
        assert deferred is not None
        assert deferred.status == JobStatus.DEFERRED

        await monitor.record_failed(
            job_id="job-test-2",
            error="final",
            attempt=3,
            max_tries=3,
        )
        failed = await monitor.get("job-test-2")
        assert failed is not None
        assert failed.status == JobStatus.FAILED
        assert failed.error == "final"
    finally:
        await redis.delete("job:status:job-test-2")
        await redis.zrem("jobs:recent", "job-test-2")
        await redis.aclose()
