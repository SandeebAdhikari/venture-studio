"""Unit tests for readiness check helpers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.observability.readiness import (
    check_scheduler_availability,
    check_worker_availability,
    run_readiness_checks,
)


@pytest.mark.asyncio
async def test_worker_check_optional_by_default() -> None:
    settings = Settings(worker_readiness_required=False)
    result = await check_worker_availability(AsyncMock(), settings)
    assert result.status == "ok"
    assert result.detail == "not required"


@pytest.mark.asyncio
async def test_worker_check_requires_heartbeat() -> None:
    class EmptyAsyncIter:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    redis = AsyncMock()
    redis.scan_iter = MagicMock(return_value=EmptyAsyncIter())

    settings = Settings(worker_readiness_required=True)
    result = await check_worker_availability(redis, settings)
    assert result.status == "error"


def test_scheduler_check_when_disabled() -> None:
    settings = Settings(scheduler_enabled=False)
    result = check_scheduler_availability(settings)
    assert result.status == "ok"
    assert result.detail == "disabled"


@pytest.mark.asyncio
async def test_run_readiness_checks_returns_all_components() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=1)))
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)

    class EmptyAsyncIter:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    redis.scan_iter = MagicMock(return_value=EmptyAsyncIter())

    settings = Settings(scheduler_enabled=False, worker_readiness_required=False)
    results = await run_readiness_checks(db=db, redis=redis, settings=settings)
    assert [item.name for item in results] == [
        "postgresql",
        "redis",
        "worker",
        "scheduler",
    ]
    assert all(item.status == "ok" for item in results)
