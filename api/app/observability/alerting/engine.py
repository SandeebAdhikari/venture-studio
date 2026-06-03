"""Alert engine: cooldown, deduplication, and multi-provider delivery."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import Settings, get_settings
from app.logging import get_logger
from app.observability.alerting.cooldown import (
    COOLDOWN_KEY_PREFIX,
    CooldownStore,
    InMemoryCooldownStore,
    RedisCooldownStore,
)
from app.observability.alerting.metrics import (
    configure_alert_metrics,
    record_alert_fired,
    record_alert_suppressed,
    record_provider_error,
)
from app.observability.alerting.models import Alert, AlertType
from app.observability.alerting.providers.email import EmailAlertProvider
from app.observability.alerting.providers.logging_provider import LoggingAlertProvider
from app.observability.alerting.providers.slack import SlackAlertProvider
from app.observability.alerting.providers.webhook import WebhookAlertProvider
from app.observability.alerting.validation import validate_alert_config

if TYPE_CHECKING:
    from app.observability.alerting.providers.base import AlertProvider

logger = get_logger(__name__)

_engine: AlertEngine | None = None


def _default_cooldowns(settings: Settings) -> dict[AlertType, int]:
    return {
        AlertType.WORKER_OFFLINE: settings.alert_worker_offline_cooldown_sec,
        AlertType.SCHEDULER_OFFLINE: settings.alert_scheduler_offline_cooldown_sec,
        AlertType.PIPELINE_FAILURE: settings.alert_pipeline_failure_cooldown_sec,
        AlertType.PIPELINE_STALL: settings.alert_pipeline_stall_cooldown_sec,
        AlertType.QUEUE_BACKLOG_GROWTH: settings.alert_queue_backlog_cooldown_sec,
        AlertType.LLM_BUDGET_EXHAUSTED: settings.alert_llm_budget_cooldown_sec,
        AlertType.COLLECTOR_REPEATED_FAILURE: settings.alert_collector_failure_cooldown_sec,
    }


def build_providers(settings: Settings) -> list[AlertProvider]:
    validation = validate_alert_config(settings)
    for warning in validation.warnings:
        logger.warning("Alert config: %s", warning)
    for error in validation.errors:
        logger.error("Alert config: %s", error)

    providers: list[AlertProvider] = []
    for name in settings.alert_provider_names:
        if name == "logging":
            providers.append(LoggingAlertProvider())
        elif name == "webhook":
            if "webhook" in validation.active_providers:
                providers.append(WebhookAlertProvider(settings))
            else:
                logger.warning(
                    "Alert provider 'webhook' skipped: configure ALERT_WEBHOOK_URL "
                    "with a valid http(s) URL"
                )
        elif name == "slack":
            if "slack" in validation.active_providers:
                providers.append(SlackAlertProvider(settings))
            else:
                logger.warning(
                    "Alert provider 'slack' skipped: configure ALERT_SLACK_WEBHOOK_URL "
                    "with a valid Slack incoming webhook URL"
                )
        elif name == "email":
            providers.append(EmailAlertProvider())
        else:
            logger.warning("Unknown alert provider '%s'; skipping", name)

    if not providers:
        logger.warning("No alert providers available; using logging fallback")
        providers.append(LoggingAlertProvider())
    return providers


class AlertEngine:
    def __init__(
        self,
        *,
        settings: Settings,
        providers: list[AlertProvider],
        cooldown: CooldownStore,
    ) -> None:
        self._settings = settings
        self._providers = providers
        self._cooldown = cooldown
        self._cooldowns = _default_cooldowns(settings)
        self._logging_fallback = LoggingAlertProvider()

    @property
    def enabled(self) -> bool:
        return self._settings.alerting_enabled

    @property
    def provider_names(self) -> list[str]:
        return [provider.name for provider in self._providers]

    def cooldown_for(self, alert: Alert) -> int:
        if alert.cooldown_sec is not None:
            return alert.cooldown_sec
        return self._cooldowns.get(alert.alert_type, self._settings.alert_default_cooldown_sec)

    async def fire(self, alert: Alert, *, skip_cooldown: bool = False) -> bool:
        """Fire alert if not in cooldown. Returns True when delivered."""
        if not self.enabled:
            return False

        cooldown_sec = self.cooldown_for(alert)
        key = alert.cooldown_key
        if not skip_cooldown and await self._cooldown.is_suppressed(key, cooldown_sec):
            record_alert_suppressed(alert_type=alert.alert_type.value)
            return False

        delivered = False
        for provider in self._providers:
            try:
                await provider.send(alert)
                delivered = True
            except Exception as exc:
                record_provider_error(provider=provider.name)
                logger.warning(
                    "Alert provider delivery failed",
                    extra={"provider": provider.name, "alert_type": alert.alert_type.value},
                    exc_info=exc,
                )

        if (
            not delivered
            and self._settings.alert_failover_logging
            and not any(provider.name == "logging" for provider in self._providers)
        ):
            try:
                await self._logging_fallback.send(alert)
                delivered = True
                logger.info(
                    "Alert delivered via logging failover",
                    extra={"alert_type": alert.alert_type.value},
                )
            except Exception as exc:
                record_provider_error(provider=self._logging_fallback.name)
                logger.warning(
                    "Alert logging failover failed",
                    extra={"alert_type": alert.alert_type.value},
                    exc_info=exc,
                )

        if delivered:
            if not skip_cooldown:
                await self._cooldown.mark_fired(key, cooldown_sec)
            record_alert_fired(
                alert_type=alert.alert_type.value,
                severity=alert.severity.value,
            )
        return delivered


def init_alerting(
    settings: Settings | None = None,
    *,
    redis=None,
    cooldown: CooldownStore | None = None,
) -> AlertEngine:
    global _engine
    resolved = settings or get_settings()
    configure_alert_metrics(resolved)

    if cooldown is None:
        if redis is not None:
            cooldown = RedisCooldownStore(redis, resolved)
        else:
            try:
                from app.redis.client import get_redis_client

                cooldown = RedisCooldownStore(get_redis_client(), resolved)
            except RuntimeError:
                cooldown = InMemoryCooldownStore()

    _engine = AlertEngine(
        settings=resolved,
        providers=build_providers(resolved),
        cooldown=cooldown,
    )
    logger.info(
        "Alerting initialized",
        extra={
            "enabled": resolved.alerting_enabled,
            "providers": _engine.provider_names,
            "cooldown_prefix": COOLDOWN_KEY_PREFIX,
        },
    )
    return _engine


def get_alert_engine() -> AlertEngine:
    global _engine
    if _engine is None:
        return init_alerting()
    return _engine
