"""Production-only configuration validation for API startup."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import Settings
from app.observability.alerting.validation import validate_alert_config

# Known insecure placeholders — must not be used when ENVIRONMENT=production.
INSECURE_API_KEY_VALUES = frozenset(
    {
        "change-me-to-a-secure-random-string",
        "change-me",
        "ci-github-actions-api-key",
        "test-api-key",
        "test",
    }
)

PRODUCTION_API_KEY_MIN_LENGTH = 32

STARTUP_EXIT_PRODUCTION_CONFIG_INVALID = 15


@dataclass(frozen=True)
class ProductionValidationResult:
    valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def detail(self) -> str:
        parts: list[str] = []
        if self.warnings:
            parts.append(f"warnings={' | '.join(self.warnings)}")
        if self.errors:
            parts.append(f"errors={' | '.join(self.errors)}")
        return "; ".join(parts) if parts else "ok"


def validate_production_settings(settings: Settings) -> ProductionValidationResult:
    """Validate settings required for a production deployment."""
    if settings.environment != "production":
        return ProductionValidationResult(valid=True)

    errors: list[str] = []
    warnings: list[str] = []

    alert_result = validate_alert_config(settings)
    errors.extend(alert_result.errors)

    api_key = settings.api_key.strip()
    if len(api_key) < PRODUCTION_API_KEY_MIN_LENGTH:
        errors.append(
            f"API_KEY must be at least {PRODUCTION_API_KEY_MIN_LENGTH} characters in production"
        )
    if api_key.lower() in INSECURE_API_KEY_VALUES:
        errors.append("API_KEY must not use a default, test, or CI example value in production")

    if not settings.worker_readiness_required:
        errors.append("WORKER_READINESS_REQUIRED must be true in production")

    if not settings.openai_api_key.strip():
        errors.append("OPENAI_API_KEY is required in production for LLM pipeline stages")

    if settings.llm_daily_budget_usd < 5.0:
        warnings.append(
            "LLM_DAILY_BUDGET_USD below 5.0 may block full 14-stage pipeline runs"
        )

    if not settings.require_founder_approval:
        warnings.append(
            "REQUIRE_FOUNDER_APPROVAL=false enables auto-publish of venture reports "
            "(human-on-the-loop / autonomous publication)"
        )

    if settings.debug:
        warnings.append("DEBUG=true is not recommended in production")

    return ProductionValidationResult(
        valid=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def enforce_production_settings(settings: Settings) -> ProductionValidationResult:
    """Validate production settings and exit 15 when invalid."""
    import sys

    result = validate_production_settings(settings)
    for warning in result.warnings:
        print(f"WARN: Production configuration: {warning}", file=sys.stderr)
    if result.valid:
        return result

    for error in result.errors:
        print(f"ERROR: Production configuration invalid: {error}", file=sys.stderr)
    if settings.environment == "production":
        raise SystemExit(STARTUP_EXIT_PRODUCTION_CONFIG_INVALID)

    return result
