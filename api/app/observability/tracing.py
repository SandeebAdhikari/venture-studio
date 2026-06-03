"""Distributed tracing abstraction with logging and optional OpenTelemetry backends."""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.config import Settings, get_settings
from app.logging import get_logger

logger = get_logger(__name__)

_current_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_current_span_stack: ContextVar[list[str]] = ContextVar("span_stack", default=[])


@dataclass
class SpanContext:
    trace_id: str
    span_id: str
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.perf_counter)


class TracingProvider(Protocol):
    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> SpanContext: ...

    def end_span(self, span: SpanContext, *, error: BaseException | None = None) -> None: ...


class LoggingTracingProvider:
    """Default tracer that emits structured span events to application logs."""

    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> SpanContext:
        resolved_trace_id = trace_id or _current_trace_id.get() or uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        _current_trace_id.set(resolved_trace_id)
        stack = list(_current_span_stack.get())
        stack.append(name)
        _current_span_stack.set(stack)
        attrs = attributes or {}
        logger.info(
            "trace span started",
            extra={
                "trace_id": resolved_trace_id,
                "span_id": span_id,
                "span_name": name,
                "span_attributes": attrs,
            },
        )
        return SpanContext(
            trace_id=resolved_trace_id,
            span_id=span_id,
            name=name,
            attributes=attrs,
        )

    def end_span(self, span: SpanContext, *, error: BaseException | None = None) -> None:
        duration_ms = (time.perf_counter() - span.start_time) * 1000
        stack = list(_current_span_stack.get())
        if stack and stack[-1] == span.name:
            stack.pop()
        _current_span_stack.set(stack)
        extra: dict[str, Any] = {
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "span_name": span.name,
            "duration_ms": round(duration_ms, 2),
        }
        if error is not None:
            extra["error"] = str(error)
            logger.warning("trace span failed", extra=extra)
        else:
            logger.info("trace span finished", extra=extra)


class OpenTelemetryTracingProvider:
    """OpenTelemetry-backed tracer when the optional SDK is installed."""

    def __init__(self, settings: Settings) -> None:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)
        if settings.otel_exporter_endpoint:
            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(settings.otel_service_name)
        self._active: dict[str, Any] = {}

    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> SpanContext:
        del trace_id  # OTEL manages trace correlation
        otel_span = self._tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                otel_span.set_attribute(key, value)
        span_id = uuid.uuid4().hex[:16]
        resolved_trace_id = _current_trace_id.get() or uuid.uuid4().hex
        _current_trace_id.set(resolved_trace_id)
        self._active[span_id] = otel_span
        return SpanContext(
            trace_id=resolved_trace_id,
            span_id=span_id,
            name=name,
            attributes=attributes or {},
        )

    def end_span(self, span: SpanContext, *, error: BaseException | None = None) -> None:
        otel_span = self._active.pop(span.span_id, None)
        if otel_span is None:
            return
        if error is not None:
            from opentelemetry.trace import Status, StatusCode

            otel_span.record_exception(error)
            otel_span.set_status(Status(StatusCode.ERROR, str(error)))
        otel_span.end()


_tracer: TracingProvider | None = None


def init_tracing(settings: Settings | None = None) -> TracingProvider:
    global _tracer
    resolved = settings or get_settings()
    if not resolved.observability_tracing_enabled:
        _tracer = LoggingTracingProvider()
        return _tracer

    if resolved.observability_tracing_provider == "opentelemetry":
        try:
            _tracer = OpenTelemetryTracingProvider(resolved)
            logger.info("OpenTelemetry tracing initialized")
            return _tracer
        except ImportError:
            logger.warning(
                "OpenTelemetry packages not installed; falling back to logging tracer",
            )

    _tracer = LoggingTracingProvider()
    return _tracer


def get_tracer() -> TracingProvider:
    global _tracer
    if _tracer is None:
        return init_tracing()
    return _tracer


def get_trace_id() -> str | None:
    return _current_trace_id.get()


def set_trace_id(trace_id: str) -> None:
    _current_trace_id.set(trace_id)


@contextmanager
def trace_span(
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> Iterator[SpanContext]:
    tracer = get_tracer()
    span = tracer.start_span(name, attributes=attributes, trace_id=trace_id)
    try:
        yield span
    except BaseException as exc:
        tracer.end_span(span, error=exc)
        raise
    else:
        tracer.end_span(span)
