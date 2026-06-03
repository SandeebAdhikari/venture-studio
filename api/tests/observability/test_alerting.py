"""Unit tests for production alerting."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.config import Settings
from app.observability.alerting.checks import (
    alert_pipeline_failure,
    alert_worker_offline,
)
from app.observability.alerting.cooldown import InMemoryCooldownStore
from app.observability.alerting.engine import AlertEngine, build_providers, init_alerting
from app.observability.alerting.metrics import record_alert_fired, record_alert_suppressed
from app.observability.alerting.models import Alert, AlertSeverity, AlertType
from app.observability.alerting.providers.logging_provider import LoggingAlertProvider
from app.observability.alerting.status import check_alerting_status


class RecordingProvider:
    def __init__(self) -> None:
        self.sent: list[Alert] = []
        self.name = "recording"

    async def send(self, alert: Alert) -> None:
        self.sent.append(alert)


@pytest.fixture
def alerting_settings() -> Settings:
    return Settings(
        alerting_enabled=True,
        alert_providers="logging",
        alert_default_cooldown_sec=60,
        observability_metrics_enabled=True,
    )


@pytest.mark.asyncio
async def test_alert_engine_suppresses_duplicate_within_cooldown(
    alerting_settings: Settings,
) -> None:
    provider = RecordingProvider()
    engine = AlertEngine(
        settings=alerting_settings,
        providers=[provider],
        cooldown=InMemoryCooldownStore(),
    )
    alert = Alert(
        alert_type=AlertType.WORKER_OFFLINE,
        severity=AlertSeverity.CRITICAL,
        title="Worker offline",
        message="No workers",
        dedup_key="global",
    )

    assert await engine.fire(alert) is True
    assert len(provider.sent) == 1
    assert await engine.fire(alert) is False
    assert len(provider.sent) == 1


@pytest.mark.asyncio
async def test_build_providers_defaults_to_logging() -> None:
    settings = Settings(alert_providers="")
    providers = build_providers(settings)
    assert len(providers) == 1
    assert isinstance(providers[0], LoggingAlertProvider)


@pytest.mark.asyncio
async def test_alert_worker_offline_helper(alerting_settings: Settings) -> None:
    provider = RecordingProvider()
    engine = AlertEngine(
        settings=alerting_settings,
        providers=[provider],
        cooldown=InMemoryCooldownStore(),
    )
    assert await alert_worker_offline(engine=engine) is True
    assert provider.sent[0].alert_type == AlertType.WORKER_OFFLINE


@pytest.mark.asyncio
async def test_pipeline_failure_alert_payload(alerting_settings: Settings) -> None:
    provider = RecordingProvider()
    engine = AlertEngine(
        settings=alerting_settings,
        providers=[provider],
        cooldown=InMemoryCooldownStore(),
    )
    run_id = uuid4()
    await alert_pipeline_failure(
        pipeline_run_id=run_id,
        status="failed",
        trigger="api",
        error_summary="stage classify failed",
        engine=engine,
    )
    payload = provider.sent[0].to_payload()
    assert payload["alert_type"] == "pipeline_failure"
    assert payload["context"]["pipeline_run_id"] == str(run_id)


def test_check_alerting_status_when_disabled() -> None:
    result = check_alerting_status(Settings(alerting_enabled=False))
    assert result.status == "ok"
    assert result.detail == "disabled"


def test_init_alerting_uses_in_memory_without_redis() -> None:
    engine = init_alerting(Settings(alerting_enabled=True), cooldown=InMemoryCooldownStore())
    assert engine.enabled


@pytest.mark.asyncio
async def test_provider_error_does_not_block_other_providers(
    alerting_settings: Settings,
) -> None:
    class FailingProvider:
        name = "failing"

        async def send(self, alert: Alert) -> None:
            raise RuntimeError("delivery failed")

    recording = RecordingProvider()
    engine = AlertEngine(
        settings=alerting_settings,
        providers=[FailingProvider(), recording],
        cooldown=InMemoryCooldownStore(),
    )
    alert = Alert(
        alert_type=AlertType.SCHEDULER_OFFLINE,
        severity=AlertSeverity.CRITICAL,
        title="Scheduler offline",
        message="not running",
        dedup_key="global",
    )
    assert await engine.fire(alert) is True
    assert len(recording.sent) == 1


def test_alert_metrics_record_without_error() -> None:
    record_alert_fired(alert_type="worker_offline", severity="critical")
    record_alert_suppressed(alert_type="worker_offline")
