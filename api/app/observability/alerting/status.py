"""Alerting status for health and readiness integration."""

from __future__ import annotations

from app.config import Settings
from app.observability.alerting.engine import get_alert_engine
from app.observability.alerting.validation import validate_alert_config


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

    validation = validate_alert_config(settings)

    try:
        engine = get_alert_engine()
        provider_detail = ", ".join(engine.provider_names) or "none"
        detail_parts = [f"providers=[{provider_detail}]"]
        if validation.warnings:
            detail_parts.append(f"warnings={' | '.join(validation.warnings)}")
        if validation.errors:
            detail_parts.append(f"errors={' | '.join(validation.errors)}")

        if validation.errors:
            return AlertingStatusResult(
                name="alerting",
                status="warn",
                detail="; ".join(detail_parts),
            )
        if validation.warnings:
            return AlertingStatusResult(
                name="alerting",
                status="warn",
                detail="; ".join(detail_parts),
            )
        return AlertingStatusResult(
            name="alerting",
            status="ok",
            detail="; ".join(detail_parts),
        )
    except Exception as exc:
        return AlertingStatusResult(
            name="alerting",
            status="error",
            detail=str(exc),
        )
