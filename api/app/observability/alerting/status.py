"""Alerting status for health and readiness integration."""

from __future__ import annotations

from app.config import Settings
from app.observability.alerting.engine import get_alert_engine


class AlertingStatusResult:
    __slots__ = ("name", "status", "detail")

    def __init__(self, name: str, status: str, detail: str | None = None) -> None:
        self.name = name
        self.status = status
        self.detail = detail


def check_alerting_status(settings: Settings) -> AlertingStatusResult:
    if not settings.alerting_enabled:
        return AlertingStatusResult(
            name="alerting",
            status="ok",
            detail="disabled",
        )

    try:
        engine = get_alert_engine()
        providers = ", ".join(engine.provider_names) or "none"
        return AlertingStatusResult(
            name="alerting",
            status="ok",
            detail=f"providers=[{providers}]",
        )
    except Exception as exc:
        return AlertingStatusResult(
            name="alerting",
            status="error",
            detail=str(exc),
        )
