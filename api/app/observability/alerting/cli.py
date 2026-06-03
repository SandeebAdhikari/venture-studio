"""CLI for alert delivery verification."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.config import get_settings
from app.logging import configure_logging, get_logger
from app.observability.alerting.checks import send_test_alert
from app.observability.alerting.cooldown import InMemoryCooldownStore
from app.observability.alerting.engine import init_alerting
from app.observability.alerting.validation import enforce_alert_config, validate_alert_config

logger = get_logger(__name__)


async def _run_test_delivery() -> int:
    settings = get_settings()
    result = validate_alert_config(settings)
    for warning in result.warnings:
        logger.warning("Alert config warning: %s", warning)
    for error in result.errors:
        logger.error("Alert config error: %s", error)

    if not settings.alerting_enabled:
        print("Alerting is disabled (ALERTING_ENABLED=false)", file=sys.stderr)
        return 1

    engine = init_alerting(settings, cooldown=InMemoryCooldownStore())
    delivered = await send_test_alert(engine=engine)
    if delivered:
        print(
            f"Test alert delivered via providers: {', '.join(engine.provider_names)}",
        )
        return 0

    print("Test alert was not delivered (check provider configuration)", file=sys.stderr)
    return 1


def _run_validate() -> int:
    settings = get_settings()
    result = enforce_alert_config(settings)
    if result.valid and not result.warnings:
        print(f"Alert configuration valid: {result.detail()}")
        return 0
    if result.valid:
        for warning in result.warnings:
            print(f"WARN: {warning}")
        print(f"Alert configuration valid with warnings: {result.detail()}")
        return 0
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="AVS alerting utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("test", help="Send a test alert through configured providers")
    sub.add_parser("validate", help="Validate alert configuration")

    args = parser.parse_args(argv)
    settings = get_settings()
    configure_logging(settings)

    if args.command == "test":
        raise SystemExit(asyncio.run(_run_test_delivery()))
    if args.command == "validate":
        raise SystemExit(_run_validate())


if __name__ == "__main__":
    main()
