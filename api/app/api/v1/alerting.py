"""Alerting operational endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AppSettings
from app.observability.alerting.checks import send_test_alert
from app.observability.alerting.engine import get_alert_engine
from app.observability.alerting.status import check_alerting_status
from app.observability.alerting.validation import validate_alert_config

router = APIRouter(prefix="/observability/alerts", tags=["observability"])


class AlertingStatusResponse(BaseModel):
    status: str
    detail: str | None = None
    configured_providers: list[str] = Field(default_factory=list)
    active_providers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class TestAlertResponse(BaseModel):
    delivered: bool
    providers: list[str] = Field(default_factory=list)


@router.get(
    "/status",
    response_model=AlertingStatusResponse,
    summary="Alerting subsystem status",
)
async def alerting_status(settings: AppSettings) -> AlertingStatusResponse:
    result = check_alerting_status(settings)
    validation = validate_alert_config(settings)
    return AlertingStatusResponse(
        status=result.status,
        detail=result.detail,
        configured_providers=list(validation.configured_providers),
        active_providers=list(validation.active_providers),
        warnings=list(validation.warnings),
        errors=list(validation.errors),
    )


@router.post(
    "/test",
    response_model=TestAlertResponse,
    summary="Send a test alert",
    description=(
        "Delivers a test alert through all configured providers. "
        "Bypasses cooldown so it can be used for delivery verification."
    ),
)
async def test_alert_delivery(settings: AppSettings) -> TestAlertResponse:
    if not settings.alerting_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alerting is disabled (ALERTING_ENABLED=false)",
        )

    validation = validate_alert_config(settings)
    if validation.errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(validation.errors),
        )

    engine = get_alert_engine()
    delivered = await send_test_alert(engine=engine)
    return TestAlertResponse(delivered=delivered, providers=engine.provider_names)
