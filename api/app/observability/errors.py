"""Error tracking abstraction for Sentry and OpenTelemetry."""

from __future__ import annotations

from typing import Any, Protocol

from app.config import Settings, get_settings
from app.logging import get_logger

logger = get_logger(__name__)


class ErrorTracker(Protocol):
    def capture_exception(
        self,
        exc: BaseException,
        *,
        context: dict[str, Any] | None = None,
    ) -> None: ...

    def capture_message(
        self,
        message: str,
        *,
        level: str = "error",
        context: dict[str, Any] | None = None,
    ) -> None: ...


class NoopErrorTracker:
    def capture_exception(
        self,
        exc: BaseException,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        del exc, context

    def capture_message(
        self,
        message: str,
        *,
        level: str = "error",
        context: dict[str, Any] | None = None,
    ) -> None:
        del message, level, context


class SentryErrorTracker:
    def __init__(self, settings: Settings) -> None:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            integrations=[LoggingIntegration(level=None, event_level=None)],
            traces_sample_rate=settings.sentry_traces_sample_rate,
        )
        self._sdk = sentry_sdk

    def capture_exception(
        self,
        exc: BaseException,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        with self._sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            self._sdk.capture_exception(exc)

    def capture_message(
        self,
        message: str,
        *,
        level: str = "error",
        context: dict[str, Any] | None = None,
    ) -> None:
        with self._sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            self._sdk.capture_message(message, level=level)


class OpenTelemetryErrorTracker:
    """Records exceptions on the active OpenTelemetry span."""

    def capture_exception(
        self,
        exc: BaseException,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span is not None:
            span.record_exception(exc)
            if context:
                for key, value in context.items():
                    span.set_attribute(f"error.{key}", str(value))

    def capture_message(
        self,
        message: str,
        *,
        level: str = "error",
        context: dict[str, Any] | None = None,
    ) -> None:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span is not None:
            span.add_event(
                message,
                attributes={"level": level, **({} if context is None else context)},
            )


_tracker: ErrorTracker | None = None


def init_error_tracking(settings: Settings | None = None) -> ErrorTracker:
    global _tracker
    resolved = settings or get_settings()
    provider = resolved.observability_error_tracking_provider

    if provider == "sentry" and resolved.sentry_dsn:
        try:
            _tracker = SentryErrorTracker(resolved)
            logger.info("Sentry error tracking initialized")
            return _tracker
        except ImportError:
            logger.warning("sentry-sdk not installed; error tracking disabled")

    if provider == "opentelemetry":
        try:
            _tracker = OpenTelemetryErrorTracker()
            logger.info("OpenTelemetry error tracking initialized")
            return _tracker
        except ImportError:
            logger.warning("OpenTelemetry packages not installed; error tracking disabled")

    _tracker = NoopErrorTracker()
    return _tracker


def get_error_tracker() -> ErrorTracker:
    global _tracker
    if _tracker is None:
        return init_error_tracking()
    return _tracker


def capture_exception(
    exc: BaseException,
    *,
    context: dict[str, Any] | None = None,
) -> None:
    get_error_tracker().capture_exception(exc, context=context)
