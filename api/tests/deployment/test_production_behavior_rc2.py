"""RC2: production mode validation behavior matrix (no feature code)."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.deployment.bootstrap import (
    STARTUP_EXIT_ALERT_CONFIG_INVALID,
    STARTUP_EXIT_PRODUCTION_CONFIG_INVALID,
    check_postgresql_sync,
    check_redis_sync,
)
from app.deployment.production_validation import (
    enforce_production_settings,
    validate_production_settings,
)
from app.observability.alerting.validation import (
    enforce_alert_config,
    validate_alert_config,
)


def _valid_production_base(**overrides) -> Settings:
    defaults = dict(
        environment="production",
        api_key="x" * 40,
        openai_api_key="sk-prod-valid-key",
        alerting_enabled=True,
        alert_providers="slack,webhook,logging",
        alert_slack_webhook_url="https://hooks.slack.com/services/T/B/X",
        alert_webhook_url="https://hooks.example/alerts",
        worker_readiness_required=True,
        require_founder_approval=True,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def test_production_valid_config_passes_validation() -> None:
    result = validate_production_settings(_valid_production_base())
    assert result.valid
    assert not result.errors


def test_local_default_skips_production_rules() -> None:
    result = validate_production_settings(
        Settings(
            environment="local",
            api_key="ci-github-actions-api-key",
            alert_providers="logging",
            worker_readiness_required=False,
        )
    )
    assert result.valid


@pytest.mark.parametrize(
    ("overrides", "error_substrings"),
    [
        (
            {"alert_providers": "slack", "alert_slack_webhook_url": ""},
            ["ALERT_SLACK_WEBHOOK_URL"],
        ),
        (
            {"alert_providers": "webhook", "alert_webhook_url": ""},
            ["ALERT_WEBHOOK_URL"],
        ),
        (
            {"alert_providers": "logging"},
            ["external"],
        ),
        (
            {"api_key": "x" * 16},
            ["API_KEY", "32"],
        ),
        (
            {"api_key": "ci-github-actions-api-key"},
            ["API_KEY"],
        ),
        (
            {"worker_readiness_required": False},
            ["WORKER_READINESS_REQUIRED"],
        ),
        (
            {"openai_api_key": ""},
            ["OPENAI_API_KEY"],
        ),
    ],
)
def test_production_rejects_misconfiguration(
    overrides: dict,
    error_substrings: list[str],
) -> None:
    result = validate_production_settings(_valid_production_base(**overrides))
    assert not result.valid
    combined = " ".join(result.errors).lower()
    for needle in error_substrings:
        assert needle.lower() in combined


def test_slack_only_satisfies_external_delivery() -> None:
    result = validate_production_settings(
        _valid_production_base(
            alert_providers="slack,logging",
            alert_webhook_url="",
        )
    )
    assert result.valid


def test_enforce_alert_config_exits_14_before_production_15() -> None:
    settings = _valid_production_base(alert_providers="logging")
    with pytest.raises(SystemExit) as exc:
        enforce_alert_config(settings)
    assert exc.value.code == STARTUP_EXIT_ALERT_CONFIG_INVALID


def test_enforce_production_exits_15_on_api_key() -> None:
    settings = _valid_production_base(api_key="ci-github-actions-api-key")
    with pytest.raises(SystemExit) as exc:
        enforce_production_settings(settings)
    assert exc.value.code == STARTUP_EXIT_PRODUCTION_CONFIG_INVALID


def test_alert_enforcement_active_only_in_production() -> None:
    local = validate_alert_config(
        Settings(environment="local", alerting_enabled=True, alert_providers="logging")
    )
    assert local.valid
    prod = validate_alert_config(
        Settings(environment="production", alerting_enabled=True, alert_providers="logging")
    )
    assert not prod.valid


def test_postgresql_sync_fails_on_unreachable_host() -> None:
    settings = Settings(
        api_key="test-key-at-least-sixteen",
        postgres_host="127.0.0.1",
        postgres_port=59999,
    )
    ok, err = check_postgresql_sync(settings)
    assert ok is False
    assert err


def test_redis_sync_fails_on_unreachable_host() -> None:
    settings = Settings(
        api_key="test-key-at-least-sixteen",
        redis_host="127.0.0.1",
        redis_port=59998,
    )
    ok, err = check_redis_sync(settings)
    assert ok is False
    assert err
