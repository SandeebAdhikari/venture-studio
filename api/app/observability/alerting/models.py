"""Alert models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    WORKER_OFFLINE = "worker_offline"
    SCHEDULER_OFFLINE = "scheduler_offline"
    PIPELINE_FAILURE = "pipeline_failure"
    PIPELINE_STALL = "pipeline_stall"
    QUEUE_BACKLOG_GROWTH = "queue_backlog_growth"
    LLM_BUDGET_EXHAUSTED = "llm_budget_exhausted"
    COLLECTOR_REPEATED_FAILURE = "collector_repeated_failure"


class Alert(BaseModel):
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    dedup_key: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    cooldown_sec: int | None = None

    @property
    def cooldown_key(self) -> str:
        return f"{self.alert_type.value}:{self.dedup_key}"

    def to_payload(self) -> dict[str, Any]:
        return {
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "dedup_key": self.dedup_key,
            "context": self.context,
        }
