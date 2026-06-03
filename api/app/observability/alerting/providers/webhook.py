"""Generic webhook alert provider."""

from __future__ import annotations

import httpx

from app.config import Settings
from app.observability.alerting.models import Alert
from app.observability.alerting.validation import is_http_url, parse_webhook_headers


class WebhookAlertProvider:
    name = "webhook"

    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None) -> None:
        self._url = settings.alert_webhook_url.strip()
        self._timeout_sec = settings.alert_webhook_timeout_sec
        self._client = client
        headers, error = parse_webhook_headers(settings.alert_webhook_headers)
        if error:
            raise ValueError(error)
        self._headers = headers
        if not self._url:
            raise ValueError(
                "ALERT_WEBHOOK_URL is required when webhook provider is enabled"
            )
        if not is_http_url(self._url):
            raise ValueError("ALERT_WEBHOOK_URL must be a valid http(s) URL")

    async def send(self, alert: Alert) -> None:
        payload = alert.to_payload()
        if self._client is not None:
            response = await self._client.post(
                self._url,
                json=payload,
                headers=self._headers or None,
                timeout=self._timeout_sec,
            )
            response.raise_for_status()
            return

        async with httpx.AsyncClient(timeout=self._timeout_sec) as client:
            response = await client.post(
                self._url,
                json=payload,
                headers=self._headers or None,
            )
            response.raise_for_status()
