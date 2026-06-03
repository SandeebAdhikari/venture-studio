"""Production alerting on top of observability."""

from app.observability.alerting.checks import (
    alert_collector_repeated_failure,
    alert_llm_budget_exhausted,
    alert_pipeline_failure,
    alert_pipeline_stall,
    alert_queue_backlog_growth,
    alert_scheduler_offline,
    alert_worker_offline,
)
from app.observability.alerting.engine import AlertEngine, get_alert_engine, init_alerting
from app.observability.alerting.models import Alert, AlertSeverity, AlertType

__all__ = [
    "Alert",
    "AlertEngine",
    "AlertSeverity",
    "AlertType",
    "alert_collector_repeated_failure",
    "alert_llm_budget_exhausted",
    "alert_pipeline_failure",
    "alert_pipeline_stall",
    "alert_queue_backlog_growth",
    "alert_scheduler_offline",
    "alert_worker_offline",
    "get_alert_engine",
    "init_alerting",
]
