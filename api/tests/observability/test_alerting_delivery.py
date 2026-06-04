"""Tests for alert config validation, delivery, failover, and categories."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.config import Settings
from app.observability.alerting.checks import (
    alert_collector_repeated_failure,
    alert_llm_budget_exhausted,
    alert_pipeline_failure,
    alert_pipeline_stall,
    alert_queue_backlog_growth,
    alert_scheduler_offline,
    alert_worker_offline,
    send_test_alert,
)
from app.observability.alerting.cooldown import InMemoryCooldownStore
from app.observability.alerting.engine import AlertEngine, build_providers, init_alerting
from app.observability.alerting.models import Alert, AlertSeverity, AlertType
from app.observability.alerting.providers.logging_provider import LoggingAlertProvider
from app.observability.alerting.providers.slack import SlackAlertProvider
from app.observability.alerting.providers.webhook import WebhookAlertProvider
from app.observability.alerting.status import check_alerting_status
from app.observability.alerting.validation import (
    enforce_alert_config,
    parse_webhook_headers,
    should_fail_on_alert_errors,
    validate_alert_config,
)


class RecordingProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.sent: list[Alert] = []
        self.fail = fail
        self.name = "recording"

    async def send(self, alert: Alert) -> None:
        if self.fail:
            raise RuntimeError("delivery failed")
        self.sent.append(alert)


@pytest.mark.parametrize(
    ("providers", "webhook_url", "slack_url", "expect_error"),
    [
        ("webhook", "", "", True),
        ("slack", "", "", True),
        ("webhook", "not-a-url", "", True),
        ("slack", "", "ftp://bad.example/hook", True),
        ("logging", "", "", False),
        ("webhook,logging", "https://hooks.example/alerts", "", False),
    ],
)
def test_validate_alert_config_provider_urls(
    providers: str,
    webhook_url: str,
    slack_url: str,
    expect_error: bool,
) -> None:
    settings = Settings(
        alerting_enabled=True,
        alert_providers=providers,
        alert_webhook_url=webhook_url,
        alert_slack_webhook_url=slack_url,
    )
    result = validate_alert_config(settings)
    assert (len(result.errors) > 0) is expect_error


def test_production_requires_external_delivery() -> None:
    settings = Settings(
        environment="production",
        alerting_enabled=True,
        alert_providers="logging",
    )
    result = validate_alert_config(settings)
    assert len(result.errors) > 0
    assert "external" in result.errors[0].lower()


def test_should_fail_on_alert_errors_strict_or_production() -> None:
    assert should_fail_on_alert_errors(
        Settings(alert_validation_strict=True, environment="local")
    )
    assert should_fail_on_alert_errors(
        Settings(
            environment="production",
            alerting_enabled=True,
            alert_validation_strict=False,
        )
    )
    assert not should_fail_on_alert_errors(
        Settings(environment="local", alerting_enabled=True)
    )
    assert not should_fail_on_alert_errors(
        Settings(environment="production", alerting_enabled=False)
    )


def test_enforce_production_exits_without_external() -> None:
    settings = Settings(
        environment="production",
        alerting_enabled=True,
        alert_providers="logging",
    )
    with pytest.raises(SystemExit) as exc:
        enforce_alert_config(settings)
    assert exc.value.code == 14


def test_parse_webhook_headers_invalid_json() -> None:
    headers, error = parse_webhook_headers("{bad")
    assert headers == {}
    assert error is not None


def test_parse_webhook_headers_valid() -> None:
    headers, error = parse_webhook_headers('{"Authorization":"Bearer token"}')
    assert error is None
    assert headers == {"Authorization": "Bearer token"}


def test_slack_provider_requires_url() -> None:
    with pytest.raises(ValueError, match="ALERT_SLACK_WEBHOOK_URL"):
        SlackAlertProvider(Settings(alert_slack_webhook_url=""))


def test_webhook_provider_requires_valid_url() -> None:
    with pytest.raises(ValueError, match="ALERT_WEBHOOK_URL"):
        WebhookAlertProvider(Settings(alert_webhook_url=""))


def test_build_providers_skips_misconfigured_webhook() -> None:
    settings = Settings(
        alerting_enabled=True,
        alert_providers="webhook,logging",
        alert_webhook_url="",
    )
    providers = build_providers(settings)
    names = [provider.name for provider in providers]
    assert names == ["logging"]


@pytest.mark.asyncio
async def test_failover_to_logging_when_all_providers_fail() -> None:
    settings = Settings(
        alerting_enabled=True,
        alert_failover_logging=True,
    )
    failing = RecordingProvider(fail=True)
    engine = AlertEngine(
        settings=settings,
        providers=[failing],
        cooldown=InMemoryCooldownStore(),
    )

    with patch.object(engine._logging_fallback, "send", new_callable=AsyncMock) as mock_send:
        alert = Alert(
            alert_type=AlertType.PIPELINE_FAILURE,
            severity=AlertSeverity.CRITICAL,
            title="Pipeline failed",
            message="boom",
            dedup_key="run-1",
        )
        assert await engine.fire(alert) is True
        mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_cooldown_prevents_alert_storm() -> None:
    provider = RecordingProvider()
    engine = AlertEngine(
        settings=Settings(alerting_enabled=True, alert_default_cooldown_sec=300),
        providers=[provider],
        cooldown=InMemoryCooldownStore(),
    )
    alert = Alert(
        alert_type=AlertType.QUEUE_BACKLOG_GROWTH,
        severity=AlertSeverity.WARNING,
        title="Queue backlog",
        message="depth growing",
        dedup_key="global",
    )

    for _ in range(5):
        await engine.fire(alert)

    assert len(provider.sent) == 1


@pytest.mark.asyncio
async def test_send_test_alert_bypasses_cooldown() -> None:
    provider = RecordingProvider()
    engine = AlertEngine(
        settings=Settings(alerting_enabled=True, alert_default_cooldown_sec=300),
        providers=[provider],
        cooldown=InMemoryCooldownStore(),
    )

    assert await send_test_alert(engine=engine) is True
    assert await send_test_alert(engine=engine) is True
    assert len(provider.sent) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("helper", "expected_type"),
    [
        (alert_worker_offline, AlertType.WORKER_OFFLINE),
        (alert_scheduler_offline, AlertType.SCHEDULER_OFFLINE),
        (alert_pipeline_failure, AlertType.PIPELINE_FAILURE),
        (alert_queue_backlog_growth, AlertType.QUEUE_BACKLOG_GROWTH),
        (alert_llm_budget_exhausted, AlertType.LLM_BUDGET_EXHAUSTED),
        (alert_collector_repeated_failure, AlertType.COLLECTOR_REPEATED_FAILURE),
        (alert_pipeline_stall, AlertType.PIPELINE_STALL),
    ],
)
async def test_alert_category_helpers(helper, expected_type) -> None:
    provider = RecordingProvider()
    engine = AlertEngine(
        settings=Settings(alerting_enabled=True),
        providers=[provider],
        cooldown=InMemoryCooldownStore(),
    )

    if helper is alert_queue_backlog_growth:
        await helper(queue_depth=20, previous_depth=10, delta=10, engine=engine)
    elif helper is alert_llm_budget_exhausted:
        await helper(spent_usd=1.5, budget_usd=2.0, threshold_pct=75, engine=engine)
    elif helper is alert_collector_repeated_failure:
        source_id = uuid4()
        await helper(
            source_id=source_id,
            source_name="HN",
            source_type="hn_algolia",
            failure_count=3,
            last_error="timeout",
            engine=engine,
        )
    elif helper is alert_pipeline_stall:
        await helper(
            pipeline_run_id=uuid4(),
            stall_sec=4000,
            started_at="2026-06-03T12:00:00+00:00",
            engine=engine,
        )
    elif helper is alert_pipeline_failure:
        await helper(
            pipeline_run_id=uuid4(),
            status="failed",
            trigger="manual",
            error_summary="stage timeout",
            engine=engine,
        )
    else:
        await helper(engine=engine)

    assert provider.sent[0].alert_type == expected_type


def test_check_alerting_status_production_errors() -> None:
    init_alerting(
        Settings(
            environment="production",
            alerting_enabled=True,
            alert_providers="logging",
        ),
        cooldown=InMemoryCooldownStore(),
    )
    result = check_alerting_status(
        Settings(
            environment="production",
            alerting_enabled=True,
            alert_providers="logging",
        )
    )
    assert result.status == "error"
    assert "errors=" in (result.detail or "")


def test_check_alerting_status_warns_on_misconfiguration() -> None:
    init_alerting(
        Settings(
            alerting_enabled=True,
            alert_providers="webhook",
            alert_webhook_url="",
        ),
        cooldown=InMemoryCooldownStore(),
    )
    result = check_alerting_status(
        Settings(
            alerting_enabled=True,
            alert_providers="webhook",
            alert_webhook_url="",
        )
    )
    assert result.status == "warn"
    assert "errors=" in (result.detail or "")


def test_enforce_alert_config_strict_exits() -> None:
    settings = Settings(
        alerting_enabled=True,
        alert_providers="slack",
        alert_slack_webhook_url="",
        alert_validation_strict=True,
    )
    with pytest.raises(SystemExit) as exc:
        enforce_alert_config(settings)
    assert exc.value.code == 14


@pytest.mark.asyncio
async def test_webhook_provider_sends_headers() -> None:
    settings = Settings(
        alert_webhook_url="https://hooks.example/alerts",
        alert_webhook_headers='{"Authorization":"Bearer secret"}',
    )
    provider = WebhookAlertProvider(settings)
    alert = Alert(
        alert_type=AlertType.WORKER_OFFLINE,
        severity=AlertSeverity.CRITICAL,
        title="Worker offline",
        message="none",
        dedup_key="global",
    )

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    provider = WebhookAlertProvider(settings, client=mock_client)

    await provider.send(alert)

    mock_client.post.assert_awaited_once()
    _, kwargs = mock_client.post.await_args
    assert kwargs["headers"] == {"Authorization": "Bearer secret"}


@pytest.mark.asyncio
async def test_slack_provider_posts_payload() -> None:
    settings = Settings(alert_slack_webhook_url="https://hooks.slack.com/services/XXX/YYY/ZZZ")
    provider = SlackAlertProvider(settings)
    alert = Alert(
        alert_type=AlertType.SCHEDULER_OFFLINE,
        severity=AlertSeverity.CRITICAL,
        title="Scheduler offline",
        message="not running",
        dedup_key="global",
    )

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    provider._client = mock_client

    await provider.send(alert)

    mock_client.post.assert_awaited_once()
    args, kwargs = mock_client.post.await_args
    assert args[0] == settings.alert_slack_webhook_url
    assert "Scheduler offline" in kwargs["json"]["text"]
