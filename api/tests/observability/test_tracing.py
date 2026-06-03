"""Tests for tracing helpers."""

from app.observability.tracing import get_trace_id, set_trace_id, trace_span


def test_trace_span_sets_trace_id() -> None:
    set_trace_id("abc123")
    with trace_span("test.operation", attributes={"key": "value"}) as span:
        assert span.trace_id == "abc123"
        assert span.name == "test.operation"
    assert get_trace_id() == "abc123"
