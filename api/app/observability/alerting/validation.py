"""Startup validation for alert configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.config import Settings

KNOWN_PROVIDERS = frozenset({"logging", "webhook", "slack", "email"})


@dataclass(frozen=True)
class AlertConfigValidationResult:
    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    configured_providers: tuple[str, ...] = field(default_factory=tuple)
    active_providers: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    def detail(self) -> str:
        parts: list[str] = []
        if self.active_providers:
            parts.append(f"providers=[{', '.join(self.active_providers)}]")
        if self.warnings:
            parts.append(f"warnings={' | '.join(self.warnings)}")
        if self.errors:
            parts.append(f"errors={' | '.join(self.errors)}")
        return "; ".join(parts) if parts else "ok"


def is_http_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def parse_webhook_headers(raw: str) -> tuple[dict[str, str], str | None]:
    """Parse ALERT_WEBHOOK_HEADERS JSON. Returns (headers, error_message)."""
    text = raw.strip()
    if not text:
        return {}, None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return {}, f"ALERT_WEBHOOK_HEADERS must be valid JSON: {exc.msg}"
    if not isinstance(parsed, dict):
        return {}, "ALERT_WEBHOOK_HEADERS must be a JSON object"
    headers: dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(key, str) or not isinstance(value, str):
            return {}, "ALERT_WEBHOOK_HEADERS keys and values must be strings"
        headers[key] = value
    return headers, None


def validate_alert_config(settings: Settings) -> AlertConfigValidationResult:
    """Validate alert provider configuration for startup and health checks."""
    if not settings.alerting_enabled:
        return AlertConfigValidationResult(valid=True, active_providers=("disabled",))

    errors: list[str] = []
    warnings: list[str] = []
    configured = tuple(settings.alert_provider_names)
    active: list[str] = []

    for name in configured:
        if name not in KNOWN_PROVIDERS:
            warnings.append(f"Unknown alert provider '{name}' will be skipped")
            continue

        if name == "logging":
            active.append(name)
        elif name == "email":
            active.append(name)
            warnings.append(
                "Email provider is a stub; alerts are logged only until SMTP is configured"
            )
        elif name == "webhook":
            url = settings.alert_webhook_url.strip()
            if not url:
                errors.append(
                    "ALERT_WEBHOOK_URL is required when 'webhook' is listed in ALERT_PROVIDERS"
                )
            elif not is_http_url(url):
                errors.append("ALERT_WEBHOOK_URL must be a valid http(s) URL")
            else:
                _, header_err = parse_webhook_headers(settings.alert_webhook_headers)
                if header_err:
                    errors.append(header_err)
                else:
                    active.append(name)
        elif name == "slack":
            url = settings.alert_slack_webhook_url.strip()
            if not url:
                errors.append(
                    "ALERT_SLACK_WEBHOOK_URL is required when 'slack' is listed in "
                    "ALERT_PROVIDERS"
                )
            elif not is_http_url(url):
                errors.append("ALERT_SLACK_WEBHOOK_URL must be a valid http(s) URL")
            elif "hooks.slack.com" not in url and settings.environment == "production":
                warnings.append(
                    "ALERT_SLACK_WEBHOOK_URL does not look like a Slack incoming webhook"
                )
            else:
                active.append(name)

    if not active:
        active.append("logging")
        if configured:
            warnings.append("No usable providers configured; falling back to logging")

    external = [name for name in active if name in {"webhook", "slack"}]
    if settings.environment == "production" and not external:
        warnings.append(
            "Production alerting has no external delivery (webhook/slack); "
            "only logging will receive alerts"
        )

    return AlertConfigValidationResult(
        valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        configured_providers=configured,
        active_providers=tuple(active),
    )


def enforce_alert_config(settings: Settings) -> AlertConfigValidationResult:
    """Validate alert config and raise SystemExit when strict mode fails."""
    result = validate_alert_config(settings)
    if result.valid:
        return result

    if settings.alert_validation_strict:
        import sys

        for error in result.errors:
            print(f"ERROR: Alert configuration invalid: {error}", file=sys.stderr)
        raise SystemExit(14)

    return result
