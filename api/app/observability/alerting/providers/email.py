"""Email alert provider stub for future SMTP integration."""

from __future__ import annotations

from app.logging import get_logger
from app.observability.alerting.models import Alert

logger = get_logger(__name__)


class EmailAlertProvider:
    name = "email"

    async def send(self, alert: Alert) -> None:
        logger.info(
            "Email alerting is not configured; alert logged only",
            extra={
                "alert_type": alert.alert_type.value,
                "title": alert.title,
                "dedup_key": alert.dedup_key,
            },
        )
