"""Logging alert provider."""

from __future__ import annotations

from app.logging import get_logger
from app.observability.alerting.models import Alert, AlertSeverity

logger = get_logger(__name__)


class LoggingAlertProvider:
    name = "logging"

    async def send(self, alert: Alert) -> None:
        log_fn = logger.warning
        if alert.severity == AlertSeverity.CRITICAL:
            log_fn = logger.error
        elif alert.severity == AlertSeverity.INFO:
            log_fn = logger.info

        log_fn(
            "Operational alert",
            extra={
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "alert_message": alert.message,
                "dedup_key": alert.dedup_key,
                **alert.context,
            },
        )
