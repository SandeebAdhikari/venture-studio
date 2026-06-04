"""RC3: production-realistic alerting validation (monitor, routing, cooldown, wiring)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.config import Settings
from app.observability.alerting.checks import alert_worker_offline
from app.observability.alerting.cooldown import InMemoryCooldownStore, RedisCooldownStore
from app.observability.alerting.collector_tracker import CollectorFailureTracker
from app.observability.alerting.engine import AlertEngine, build_providers, init_alerting
from app.observability.alerting.models import Alert, AlertSeverity, AlertType
from app.observability.alerting.monitor import (
    _last_queue_depth,
    run_alert_monitor_cycle,
)
from app.observability.alerting.providers.logging_provider import LoggingAlertProvider
from app.observability.alerting.providers.slack import SlackAlertProvider
from app.observability.alerting.providers.webhook import WebhookAlertProvider
class RecordingProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.sent: list[Alert] = []
        self.fail = fail
        self.name = "recording"

    async def send(self, alert: Alert) -> None:
        if self.fail:
            raise RuntimeError("delivery failed")
        self.sent.append(alert)


@pytest.fixture(autouse=True)
def reset_monitor_queue_depth() -> None:
    import app.observability.alerting.monitor as monitor_mod

    monitor_mod._last_queue_depth = None
    yield
    monitor_mod._last_queue_depth = None


def _engine_with_recording(
    settings: Settings | None = None,
) -> tuple[AlertEngine, RecordingProvider]:
    provider = RecordingProvider()
    engine = AlertEngine(
        settings=settings or Settings(alerting_enabled=True),
        providers=[provider],
        cooldown=InMemoryCooldownStore(),
    )
    return engine, provider


@pytest.mark.asyncio
async def test_rc3_multi_provider_routing_order() -> None:
    """Slack, webhook, and logging each receive the same alert when configured."""
    slack_mock = AsyncMock()
    slack_mock.post = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))
    webhook_mock = AsyncMock()
    webhook_mock.post = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))
    logging_sent: list[Alert] = []

    async def capture_log(alert: Alert) -> None:
        logging_sent.append(alert)

    settings = Settings(
        alerting_enabled=True,
        alert_providers="slack,webhook,logging",
        alert_slack_webhook_url="https://hooks.slack.com/services/T/B/X",
        alert_webhook_url="https://hooks.example/alerts",
    )
    slack = SlackAlertProvider(settings)
    slack._client = slack_mock
    webhook = WebhookAlertProvider(settings)
    webhook._client = webhook_mock
    logging = LoggingAlertProvider()
    with patch.object(logging, "send", side_effect=capture_log):
        engine = AlertEngine(
            settings=settings,
            providers=[slack, webhook, logging],
            cooldown=InMemoryCooldownStore(),
        )
        await alert_worker_offline(engine=engine)

    assert slack_mock.post.await_count == 1
    assert webhook_mock.post.await_count == 1
    assert len(logging_sent) == 1


def test_rc3_build_providers_includes_all_when_valid() -> None:
    settings = Settings(
        alerting_enabled=True,
        alert_providers="slack,webhook,logging",
        alert_slack_webhook_url="https://hooks.slack.com/services/T/B/X",
        alert_webhook_url="https://hooks.example/alerts",
    )
    names = [p.name for p in build_providers(settings)]
    assert names == ["slack", "webhook", "logging"]


@pytest.mark.asyncio
async def test_rc3_duplicate_suppression_same_dedup_key() -> None:
    engine, provider = _engine_with_recording(
        Settings(alerting_enabled=True, alert_worker_offline_cooldown_sec=600)
    )
    await alert_worker_offline(engine=engine)
    await alert_worker_offline(engine=engine)
    assert len(provider.sent) == 1


@pytest.mark.asyncio
async def test_rc3_different_pipeline_runs_not_suppressed() -> None:
    from app.observability.alerting.checks import alert_pipeline_failure

    engine, provider = _engine_with_recording(
        Settings(alerting_enabled=True, alert_pipeline_failure_cooldown_sec=300)
    )
    await alert_pipeline_failure(
        pipeline_run_id=uuid4(),
        status="failed",
        trigger="nightly",
        engine=engine,
    )
    await alert_pipeline_failure(
        pipeline_run_id=uuid4(),
        status="failed",
        trigger="nightly",
        engine=engine,
    )
    assert len(provider.sent) == 2


@pytest.mark.asyncio
async def test_rc3_redis_cooldown_suppresses_until_expiry() -> None:
    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=0)
    redis.set = AsyncMock()
    store = RedisCooldownStore(redis, Settings(alert_cooldown_key_prefix="obs:cd:"))

    assert await store.is_suppressed("worker_offline:global", 600) is False
    await store.mark_fired("worker_offline:global", 600)
    redis.set.assert_awaited_once_with("obs:cd:worker_offline:global", "1", ex=600)

    redis.exists = AsyncMock(return_value=1)
    assert await store.is_suppressed("worker_offline:global", 600) is True


@pytest.mark.asyncio
async def test_rc3_monitor_worker_offline_delivers() -> None:
    settings = Settings(
        alerting_enabled=True,
        alert_worker_monitor_enabled=True,
        scheduler_enabled=False,
        alert_pipeline_stall_sec=0,
        alert_queue_backlog_threshold=1000,
    )
    engine, provider = _engine_with_recording(settings)
    init_alerting(settings, cooldown=InMemoryCooldownStore())

    redis = AsyncMock()
    redis.zcard = AsyncMock(return_value=0)

    class EmptyAsyncIter:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    redis.scan_iter = MagicMock(return_value=EmptyAsyncIter())

    with patch("app.observability.alerting.monitor.get_alert_engine", return_value=engine):
        await run_alert_monitor_cycle(
            redis=redis,
            session_factory=MagicMock(),
            settings=settings,
        )

    assert len(provider.sent) == 1
    assert provider.sent[0].alert_type == AlertType.WORKER_OFFLINE


@pytest.mark.asyncio
async def test_rc3_monitor_scheduler_offline() -> None:
    settings = Settings(
        alerting_enabled=True,
        alert_worker_monitor_enabled=False,
        scheduler_enabled=True,
        alert_pipeline_stall_sec=0,
    )
    engine, provider = _engine_with_recording(settings)

    redis = AsyncMock()
    redis.zcard = AsyncMock(return_value=0)

    mock_scheduler = MagicMock()
    mock_scheduler.is_running = False

    with (
        patch("app.observability.alerting.monitor.get_alert_engine", return_value=engine),
        patch("app.observability.alerting.monitor.get_scheduler", return_value=mock_scheduler),
    ):
        await run_alert_monitor_cycle(
            redis=redis,
            session_factory=MagicMock(),
            settings=settings,
        )

    assert len(provider.sent) == 1
    assert provider.sent[0].alert_type == AlertType.SCHEDULER_OFFLINE


@pytest.mark.asyncio
async def test_rc3_monitor_queue_backlog_requires_two_cycles() -> None:
    settings = Settings(
        alerting_enabled=True,
        alert_worker_monitor_enabled=False,
        scheduler_enabled=False,
        alert_pipeline_stall_sec=0,
        alert_queue_backlog_threshold=10,
        alert_queue_growth_delta=5,
    )
    engine, provider = _engine_with_recording(settings)

    redis = AsyncMock()
    redis.zcard = AsyncMock(side_effect=[8, 16])

    with patch("app.observability.alerting.monitor.get_alert_engine", return_value=engine):
        await run_alert_monitor_cycle(
            redis=redis, session_factory=MagicMock(), settings=settings
        )
        assert len(provider.sent) == 0

        await run_alert_monitor_cycle(
            redis=redis, session_factory=MagicMock(), settings=settings
        )
        assert len(provider.sent) == 1
        assert provider.sent[0].alert_type == AlertType.QUEUE_BACKLOG_GROWTH


@pytest.mark.asyncio
async def test_rc3_monitor_pipeline_stall() -> None:
    run_id = uuid4()
    started = datetime.now(UTC) - timedelta(seconds=4000)
    running = MagicMock()
    running.id = run_id
    running.started_at = started

    settings = Settings(
        alerting_enabled=True,
        alert_worker_monitor_enabled=False,
        scheduler_enabled=False,
        alert_pipeline_stall_sec=3600,
        alert_queue_backlog_threshold=1000,
    )
    engine, provider = _engine_with_recording(settings)

    redis = AsyncMock()
    redis.zcard = AsyncMock(return_value=0)

    mock_repos = MagicMock()
    mock_repos.pipelines.get_running = AsyncMock(return_value=running)

    def session_factory() -> MagicMock:
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=MagicMock())
        cm.__aexit__ = AsyncMock(return_value=None)
        return cm

    with (
        patch("app.observability.alerting.monitor.get_alert_engine", return_value=engine),
        patch("app.repositories.get_repositories", return_value=mock_repos),
    ):
        await run_alert_monitor_cycle(
            redis=redis,
            session_factory=session_factory,
            settings=settings,
        )

    assert len(provider.sent) == 1
    assert provider.sent[0].alert_type == AlertType.PIPELINE_STALL
    assert provider.sent[0].dedup_key == str(run_id)


@pytest.mark.asyncio
async def test_rc3_collector_tracker_threshold() -> None:
    redis = AsyncMock()
    redis.incr = AsyncMock(side_effect=[1, 2, 3])
    redis.expire = AsyncMock()
    settings = Settings(alert_collector_failure_threshold=3)
    tracker = CollectorFailureTracker(redis, settings)
    source_id = uuid4()

    assert await tracker.record_failure(source_id) == 1
    redis.expire.assert_awaited_once()
    assert await tracker.record_failure(source_id) == 2
    assert await tracker.record_failure(source_id) == 3


@pytest.mark.asyncio
async def test_rc3_llm_budget_emit_calls_alert_helper() -> None:
    from app.services.llm_budget import LLMBudgetService

    repos = MagicMock()
    repos.session = MagicMock()
    service = LLMBudgetService(
        repos=repos,
        settings=Settings(alerting_enabled=True, llm_daily_budget_usd=10.0),
    )

    engine, provider = _engine_with_recording(Settings(alerting_enabled=True))
    with patch("app.observability.alerting.checks.get_alert_engine", return_value=engine):
        await service._emit_budget_alert(spent_usd=7.5, threshold_pct=75)

    assert len(provider.sent) == 1
    assert provider.sent[0].alert_type == AlertType.LLM_BUDGET_EXHAUSTED
    assert provider.sent[0].dedup_key == "threshold:75"


@pytest.mark.asyncio
async def test_rc3_collector_failure_wiring() -> None:
    from app.collection.service import ComplaintCollectionService

    source_id = uuid4()
    engine, provider = _engine_with_recording(
        Settings(alerting_enabled=True, alert_collector_failure_threshold=3)
    )

    service = ComplaintCollectionService(repos=MagicMock())

    mock_tracker = MagicMock()
    mock_tracker.record_failure = AsyncMock(return_value=3)

    with (
        patch(
            "app.observability.alerting.collector_tracker.CollectorFailureTracker",
            return_value=mock_tracker,
        ),
        patch("app.redis.client.get_redis_client", return_value=AsyncMock()),
        patch(
            "app.config.get_settings",
            return_value=Settings(
                alerting_enabled=True,
                alert_collector_failure_threshold=3,
            ),
        ),
        patch("app.observability.alerting.checks.get_alert_engine", return_value=engine),
    ):
        await service._maybe_alert_collector_failure(
            source_id=source_id,
            source_name="HN",
            source_type="hn_algolia",
            error="timeout",
        )

    assert len(provider.sent) == 1
    assert provider.sent[0].alert_type == AlertType.COLLECTOR_REPEATED_FAILURE


@pytest.mark.asyncio
async def test_rc3_logging_fallback_when_slack_and_webhook_fail() -> None:
    settings = Settings(
        alerting_enabled=True,
        alert_failover_logging=True,
        alert_providers="slack,webhook",
        alert_slack_webhook_url="https://hooks.slack.com/services/T/B/X",
        alert_webhook_url="https://hooks.example/alerts",
    )
    failing_slack = SlackAlertProvider(settings)
    failing_slack._client = AsyncMock()
    failing_slack._client.post = AsyncMock(side_effect=RuntimeError("slack down"))
    failing_webhook = WebhookAlertProvider(settings)
    failing_webhook._client = AsyncMock()
    failing_webhook._client.post = AsyncMock(side_effect=RuntimeError("webhook down"))

    logging_sent: list[Alert] = []
    fallback = LoggingAlertProvider()

    async def capture(alert: Alert) -> None:
        logging_sent.append(alert)

    engine = AlertEngine(
        settings=settings,
        providers=[failing_slack, failing_webhook],
        cooldown=InMemoryCooldownStore(),
    )
    with patch.object(engine._logging_fallback, "send", side_effect=capture):
        await alert_worker_offline(engine=engine)

    assert len(logging_sent) == 1
