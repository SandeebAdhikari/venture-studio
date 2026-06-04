"""Verify logging.extra cannot use reserved LogRecord keys (production defect RC5)."""

from __future__ import annotations

import logging

import pytest

from app.config import Settings
from app.logging import configure_logging, get_logger


def test_reserved_created_in_extra_raises_with_app_logging() -> None:
    """Reproduce: opportunity batch log uses extra={'created': ...} which fails under configured logging."""
    configure_logging(Settings(log_json=True, log_level="INFO"))
    logger = get_logger("app.agents.opportunity.service")

    with pytest.raises(KeyError, match="overwrite 'created'"):
        logger.info(
            "Opportunity generation batch complete",
            extra={
                "patterns_found": 0,
                "created": 0,
                "skipped": 0,
                "failed": 0,
            },
        )


def test_opportunities_created_in_extra_succeeds_with_app_logging() -> None:
    """Regression: production fix uses opportunities_created instead of created."""
    configure_logging(Settings(log_json=True, log_level="INFO"))
    logger = get_logger("app.agents.opportunity.service")

    # Should not raise — proposed fix uses a non-reserved key
    logger.info(
        "Opportunity generation batch complete",
        extra={
            "patterns_found": 0,
            "opportunities_created": 0,
            "skipped": 0,
            "failed": 0,
        },
    )
