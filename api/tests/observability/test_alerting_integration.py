"""Integration-style tests for alerting monitor and providers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.observability.alerting.cooldown import InMemoryCooldownStore
from app.observability.alerting.engine import init_alerting
from app.observability.alerting.models import Alert, AlertSeverity, AlertType
from app.observability.alerting.monitor import get_arq_queue_depth, run_alert_monitor_cycle
from app.observability.alerting.providers.webhook import WebhookAlertProvider


@pytest.mark.asyncio
async def test_webhook_provider_posts_payload() -> None:
    settings = Settings(
        alert_webhook_url="https://hooks.example/alerts",
        alert_webhook_timeout_sec=5.0,
    )
    provider = WebhookAlertProvider(settings)
    alert = Alert(
        alert_type=AlertType.QUEUE_BACKLOG_GROWTH,
        severity=AlertSeverity.WARNING,
        title="Queue backlog",
        message="depth 25",
        dedup_key="global",
        context={"queue_depth": 25},
    )

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.observability.alerting.providers.webhook.httpx.AsyncClient",
        return_value=mock_client,
    ):
        await provider.send(alert)

    mock_client.post.assert_awaited_once()
    args, kwargs = mock_client.post.await_args
    assert args[0] == settings.alert_webhook_url
    assert kwargs["json"]["alert_type"] == "queue_backlog_growth"


@pytest.mark.asyncio
async def test_monitor_cycle_alerts_worker_offline() -> None:
    settings = Settings(
        alerting_enabled=True,
        alert_worker_monitor_enabled=True,
        scheduler_enabled=False,
        alert_queue_backlog_threshold=1000,
        alert_pipeline_stall_sec=0,
    )
    init_alerting(settings, cooldown=InMemoryCooldownStore())

    redis = AsyncMock()
    redis.llen = AsyncMock(return_value=0)

    class EmptyAsyncIter:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    redis.scan_iter = MagicMock(return_value=EmptyAsyncIter())

    session_factory = MagicMock()
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=AsyncMock())
    session_cm.__aexit__ = AsyncMock(return_value=None)
    session_factory.return_value = session_cm

    init_alerting(settings, cooldown=InMemoryCooldownStore())

    with patch(
        "app.observability.alerting.monitor.alert_worker_offline",
        new_callable=AsyncMock,
    ) as mock_alert:
        await run_alert_monitor_cycle(
            redis=redis,
            session_factory=session_factory,
            settings=settings,
        )
        mock_alert.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_arq_queue_depth() -> None:
    redis = AsyncMock()
    redis.llen = AsyncMock(return_value=7)
    depth = await get_arq_queue_depth(redis, Settings(arq_queue_name="arq:queue"))
    assert depth == 7
