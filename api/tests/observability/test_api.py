"""Tests for observability HTTP endpoints."""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.deps import get_observability_metrics_service
from app.main import app
from app.observability.readiness import ReadinessCheckResult
from app.schemas.observability import DashboardObservabilityMetricsResponse


@pytest.mark.asyncio
async def test_readiness_endpoint_reports_all_checks(client: AsyncClient, monkeypatch) -> None:
    async def fake_readiness(**kwargs):
        return [
            ReadinessCheckResult("postgresql", "ok"),
            ReadinessCheckResult("redis", "ok"),
            ReadinessCheckResult("worker", "ok", "not required"),
            ReadinessCheckResult("scheduler", "ok", "disabled"),
        ]

    monkeypatch.setattr(
        "app.api.v1.health.run_readiness_checks",
        fake_readiness,
    )

    response = await client.get("/health/ready")
    assert response.status_code == 200
    check_names = {item["name"] for item in response.json()["checks"]}
    assert check_names == {"postgresql", "redis", "worker", "scheduler"}


@pytest.mark.asyncio
async def test_readiness_returns_503_when_degraded(client: AsyncClient, monkeypatch) -> None:
    async def fake_readiness(**kwargs):
        return [
            ReadinessCheckResult("postgresql", "ok"),
            ReadinessCheckResult("worker", "error", "no active worker heartbeats"),
        ]

    monkeypatch.setattr("app.api.v1.health.run_readiness_checks", fake_readiness)

    response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(client: AsyncClient) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "avs_http_requests_total" in response.text


@pytest.mark.asyncio
async def test_dashboard_observability_metrics(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    from datetime import UTC, datetime

    async def override_observability():
        service = AsyncMock()
        service.get_dashboard_metrics = AsyncMock(
            return_value=DashboardObservabilityMetricsResponse(
                generated_at=datetime.now(UTC),
                pipeline={"running": False, "runs_total": 0, "runs_by_status": {}},
                workers={"active_count": 0, "active_worker_ids": [], "readiness_required": False},
                scheduler={"enabled": False, "running": False},
                llm={"requests_total": 0, "cost_usd_total": 0.0},
                approvals={"pending_total": 0, "by_status": {}},
                observability={"prometheus_endpoint": "/metrics"},
            )
        )
        return service

    app.dependency_overrides[get_observability_metrics_service] = override_observability
    try:
        response = await client.get("/api/v1/dashboard/metrics", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["observability"]["prometheus_endpoint"] == "/metrics"
    finally:
        app.dependency_overrides.pop(get_observability_metrics_service, None)


@pytest.mark.asyncio
async def test_request_includes_trace_header(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Trace-Id": "trace-test-001"})
    assert response.status_code == 200
    assert response.headers.get("X-Trace-Id") == "trace-test-001"
