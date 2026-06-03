"""Observability dashboard response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DashboardObservabilityMetricsResponse(BaseModel):
    generated_at: datetime
    pipeline: dict[str, Any]
    workers: dict[str, Any]
    scheduler: dict[str, Any]
    llm: dict[str, Any]
    approvals: dict[str, Any]
    observability: dict[str, Any] = Field(default_factory=dict)
