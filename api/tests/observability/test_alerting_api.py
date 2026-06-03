"""API tests for alerting endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.observability.alerting.cooldown import InMemoryCooldownStore
from app.observability.alerting.engine import init_alerting
from app.config import get_settings


@pytest.fixture(autouse=True)
def _init_alerting(monkeypatch) -> None:
    monkeypatch.setenv("ALERTING_ENABLED", "true")
    monkeypatch.setenv("ALERT_PROVIDERS", "logging")
    get_settings.cache_clear()
    init_alerting(get_settings(), cooldown=InMemoryCooldownStore())
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_alerting_status_endpoint(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.get(
        "/api/v1/observability/alerts/status",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "warn", "error"}
    assert "logging" in body["active_providers"]


@pytest.mark.asyncio
async def test_alerting_test_endpoint(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    with patch(
        "app.api.v1.alerting.send_test_alert",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_send:
        response = await client.post(
            "/api/v1/observability/alerts/test",
            headers=auth_headers,
        )
    assert response.status_code == 200
    assert response.json()["delivered"] is True
    mock_send.assert_awaited_once()
