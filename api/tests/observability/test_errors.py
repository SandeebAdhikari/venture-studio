"""Tests for error tracking abstraction."""

from app.observability.errors import NoopErrorTracker, capture_exception, init_error_tracking


def test_noop_error_tracker_does_not_raise() -> None:
    tracker = NoopErrorTracker()
    tracker.capture_exception(RuntimeError("boom"))
    tracker.capture_message("hello", level="warning")


def test_capture_exception_uses_configured_tracker(monkeypatch) -> None:
    monkeypatch.setenv("OBSERVABILITY_ERROR_TRACKING_PROVIDER", "noop")
    from app.config import get_settings

    get_settings.cache_clear()
    init_error_tracking(get_settings())
    capture_exception(ValueError("test"))
    get_settings.cache_clear()
