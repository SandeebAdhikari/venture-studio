"""Generic webhook alert provider."""

from __future__ import annotations

import httpx

from app.config import Settings
from app.observability.alerting.models import Alert


class WebhookAlertProvider:
    name = "webhook"

    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None) -> None:
        self._url = settings.alert_webhook_url.strip()
        self._timeout_sec = settings.alert_webhook_timeout_sec
        self._client = client

    async def send(self, alert: Alert) -> None:
        payload = alert.to_payload()
        if self._client is not None:
            response = await self._client.post(self._url, json=payload, timeout=self._timeout_sec)
            response.raise_for_status()
            return

        async with httpx.AsyncClient(timeout=self._timeout_sec) as client:
            response = await client.post(self._url, json=payload)
            response.raise_for_status()
