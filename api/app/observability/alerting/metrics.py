"""Prometheus metrics for alerting."""

from __future__ import annotations

from prometheus_client import Counter

from app.config import Settings

_enabled = True

ALERTS_FIRED = Counter(
    "avs_alerts_fired_total",
    "Alerts delivered to at least one provider",
    ["alert_type", "severity"],
)
ALERTS_SUPPRESSED = Counter(
    "avs_alerts_suppressed_total",
    "Alerts suppressed by cooldown or deduplication",
    ["alert_type"],
)
ALERT_PROVIDER_ERRORS = Counter(
    "avs_alert_provider_errors_total",
    "Alert provider delivery failures",
    ["provider"],
)


def configure_alert_metrics(settings: Settings) -> None:
    global _enabled
    _enabled = settings.observability_metrics_enabled


def record_alert_fired(*, alert_type: str, severity: str) -> None:
    if not _enabled:
        return
    ALERTS_FIRED.labels(alert_type=alert_type, severity=severity).inc()


def record_alert_suppressed(*, alert_type: str) -> None:
    if not _enabled:
        return
    ALERTS_SUPPRESSED.labels(alert_type=alert_type).inc()


def record_provider_error(*, provider: str) -> None:
    if not _enabled:
        return
    ALERT_PROVIDER_ERRORS.labels(provider=provider).inc()
