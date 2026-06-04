"""Tests for production configuration validation."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.deployment.production_validation import (
    enforce_production_settings,
    validate_production_settings,
)


def test_local_environment_skips_production_validation() -> None:
    result = validate_production_settings(
        Settings(
            api_key="local-dev-key-at-least-16",
            environment="local",
            worker_readiness_required=False,
        )
    )
    assert result.valid


def test_production_requires_external_alerts_and_worker_readiness() -> None:
    result = validate_production_settings(
        Settings(
            environment="production",
            api_key="a" * 32,
            openai_api_key="sk-test",
            alerting_enabled=True,
            alert_providers="logging",
            worker_readiness_required=False,
        )
    )
    assert not result.valid
    assert any("external" in err.lower() for err in result.errors)
    assert any("WORKER_READINESS" in err for err in result.errors)


def test_production_rejects_insecure_api_key() -> None:
    result = validate_production_settings(
        Settings(
            environment="production",
            api_key="change-me-to-a-secure-random-string",
            openai_api_key="sk-test",
            alert_providers="webhook",
            alert_webhook_url="https://hooks.example/alerts",
            worker_readiness_required=True,
        )
    )
    assert not result.valid
    assert any("API_KEY" in err for err in result.errors)


def test_production_valid_minimal_config() -> None:
    result = validate_production_settings(
        Settings(
            environment="production",
            api_key="x" * 40,
            openai_api_key="sk-prod-example",
            alerting_enabled=True,
            alert_providers="webhook,logging",
            alert_webhook_url="https://hooks.example/alerts",
            worker_readiness_required=True,
            require_founder_approval=True,
        )
    )
    assert result.valid


def test_enforce_production_exits_in_production() -> None:
    settings = Settings(
        environment="production",
        api_key="ci-github-actions-api-key",
        openai_api_key="sk-test",
    )
    with pytest.raises(SystemExit) as exc:
        enforce_production_settings(settings)
    assert exc.value.code == 15
