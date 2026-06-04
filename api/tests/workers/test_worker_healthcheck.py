"""Tests for worker Docker healthcheck helper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.workers.healthcheck import worker_heartbeats_healthy


@pytest.mark.asyncio
async def test_worker_heartbeats_healthy_when_workers_present() -> None:
    with (
        patch("app.workers.healthcheck.init_redis"),
        patch("app.workers.healthcheck.close_redis", new_callable=AsyncMock),
        patch("app.redis.client.get_redis_client") as mock_redis,
        patch(
            "app.workers.healthcheck.list_active_workers",
            new_callable=AsyncMock,
            return_value=["abc123"],
        ),
    ):
        mock_redis.return_value = AsyncMock()
        ok, detail = await worker_heartbeats_healthy()
    assert ok is True
    assert "1 active" in detail


@pytest.mark.asyncio
async def test_worker_heartbeats_unhealthy_when_empty() -> None:
    with (
        patch("app.workers.healthcheck.init_redis"),
        patch("app.workers.healthcheck.close_redis", new_callable=AsyncMock),
        patch("app.redis.client.get_redis_client") as mock_redis,
        patch(
            "app.workers.healthcheck.list_active_workers",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        mock_redis.return_value = AsyncMock()
        ok, detail = await worker_heartbeats_healthy()
    assert ok is False
    assert "no active" in detail


def test_healthcheck_main_exits_nonzero_when_unhealthy() -> None:
    from app.workers import healthcheck

    with patch.object(
        healthcheck,
        "worker_heartbeats_healthy",
        return_value=(False, "no workers"),
    ):
        with pytest.raises(SystemExit) as exc:
            healthcheck.main()
    assert exc.value.code == 1
