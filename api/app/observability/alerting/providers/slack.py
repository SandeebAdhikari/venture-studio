"""Slack incoming webhook alert provider."""

from __future__ import annotations

import httpx

from app.config import Settings
from app.observability.alerting.models import Alert, AlertSeverity


class SlackAlertProvider:
    name = "slack"

    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None) -> None:
        self._webhook_url = settings.alert_slack_webhook_url.strip()
        self._timeout_sec = settings.alert_webhook_timeout_sec
        self._client = client

    async def send(self, alert: Alert) -> None:
        emoji = {
            AlertSeverity.INFO: ":information_source:",
            AlertSeverity.WARNING: ":warning:",
            AlertSeverity.CRITICAL: ":rotating_light:",
        }[alert.severity]
        text = (
            f"{emoji} *[{alert.severity.value.upper()}] {alert.title}*\n"
            f"{alert.message}\n"
            f"`type={alert.alert_type.value}` `dedup={alert.dedup_key}`"
        )
        payload = {"text": text}
        if self._client is not None:
            response = await self._client.post(
                self._webhook_url,
                json=payload,
                timeout=self._timeout_sec,
            )
            response.raise_for_status()
            return

        async with httpx.AsyncClient(timeout=self._timeout_sec) as client:
            response = await client.post(self._webhook_url, json=payload)
            response.raise_for_status()
