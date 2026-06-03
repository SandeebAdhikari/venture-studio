"""Observability bootstrap for application and worker processes."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.logging import get_logger
from app.observability.errors import init_error_tracking
from app.observability.metrics import configure_metrics
from app.observability.tracing import init_tracing

logger = get_logger(__name__)
_initialized = False


def init_observability(settings: Settings | None = None) -> None:
    global _initialized
    if _initialized:
        return

    resolved = settings or get_settings()
    configure_metrics(resolved)
    init_tracing(resolved)
    init_error_tracking(resolved)
    _initialized = True
    logger.info(
        "Observability initialized",
        extra={
            "metrics_enabled": resolved.observability_metrics_enabled,
            "tracing_provider": resolved.observability_tracing_provider,
            "error_tracking_provider": resolved.observability_error_tracking_provider,
        },
    )
