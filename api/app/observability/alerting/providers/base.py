"""Alert provider protocol."""

from __future__ import annotations

from typing import Protocol

from app.observability.alerting.models import Alert


class AlertProvider(Protocol):
    name: str

    async def send(self, alert: Alert) -> None: ...
