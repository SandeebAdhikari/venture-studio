"""Unit tests for deployment bootstrap helpers."""

import pytest

from app.deployment.bootstrap import (
    MIGRATION_SUCCESS_MARKER,
    alembic_upgrade_succeeded,
    migration_marker_present,
    next_wait_interval,
    should_continue_waiting,
)


def test_alembic_upgrade_succeeded_on_zero_exit() -> None:
    assert alembic_upgrade_succeeded(0, "") is True


def test_alembic_upgrade_succeeded_fails_on_nonzero_exit() -> None:
    assert alembic_upgrade_succeeded(1, "") is False


def test_alembic_upgrade_succeeded_fails_on_traceback_in_stderr() -> None:
    assert alembic_upgrade_succeeded(0, "Traceback (most recent call last)") is False


def test_migration_marker_present() -> None:
    assert migration_marker_present(f"INFO {MIGRATION_SUCCESS_MARKER} applied")
    assert not migration_marker_present("still migrating")


@pytest.mark.parametrize(
    ("elapsed", "timeout", "expected"),
    [
        (0.0, 10.0, True),
        (9.9, 10.0, True),
        (10.0, 10.0, False),
        (11.0, 10.0, False),
    ],
)
def test_should_continue_waiting(elapsed: float, timeout: float, expected: bool) -> None:
    assert should_continue_waiting(elapsed, timeout) is expected


def test_next_wait_interval_increases_with_attempt() -> None:
    first = next_wait_interval(0, 2.0)
    later = next_wait_interval(5, 2.0)
    assert later > first
    assert later <= 10.0
