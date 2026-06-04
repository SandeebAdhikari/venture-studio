"""Regression: logging.extra must not use reserved LogRecord attribute names."""

from __future__ import annotations

import logging

import pytest

from app.config import Settings
from app.logging import configure_logging, get_logger
from app.observability.alerting.models import Alert, AlertSeverity, AlertType
from app.observability.alerting.providers.logging_provider import LoggingAlertProvider


def test_reserved_message_in_extra_raises_with_app_logging() -> None:
    configure_logging(Settings(log_json=True, log_level="INFO"))
    logger = get_logger("test.logging.extra")

    with pytest.raises(KeyError, match="overwrite 'message'"):
        logger.info("test", extra={"message": "collision"})


@pytest.mark.asyncio
async def test_alert_logging_provider_uses_safe_extra_field() -> None:
    configure_logging(Settings(log_json=True, log_level="INFO"))
    provider = LoggingAlertProvider()

    await provider.send(
        Alert(
            alert_type=AlertType.PIPELINE_FAILURE,
            severity=AlertSeverity.WARNING,
            title="Pipeline partial",
            message="Stage failed",
            dedup_key="test-run",
            context={"pipeline_run_id": "abc"},
        )
    )


@pytest.mark.asyncio
async def test_alert_logging_provider_delivers_without_reserved_context_keys() -> None:
    configure_logging(Settings(log_json=True, log_level="INFO"))
    provider = LoggingAlertProvider()

    await provider.send(
        Alert(
            alert_type=AlertType.WORKER_OFFLINE,
            severity=AlertSeverity.CRITICAL,
            title="Worker offline",
            message="No heartbeats",
            dedup_key="global",
            context={"component": "worker"},
        )
    )
