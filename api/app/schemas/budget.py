"""Pydantic schemas for LLM budget APIs."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class BudgetAgentUsage(BaseModel):
    graph_name: str
    display_name: str
    calls_total: int
    prompt_tokens_total: int
    completion_tokens_total: int
    estimated_cost_usd_total: float
    actual_cost_usd_total: float


class BudgetWarning(BaseModel):
    threshold_pct: int
    triggered: bool
    current_utilization_pct: float


class BudgetStatusResponse(BaseModel):
    usage_date: date
    enabled: bool
    budget_usd: float
    spent_usd: float
    estimated_cost_usd_total: float
    remaining_usd: float
    utilization_pct: float
    budget_exceeded: bool
    calls_total: int
    prompt_tokens_total: int
    completion_tokens_total: int
    warning_thresholds_pct: list[int]
    warnings: list[BudgetWarning]
    by_agent: list[BudgetAgentUsage]


class BudgetHistoryDay(BaseModel):
    usage_date: date
    budget_usd: float
    spent_usd: float = Field(validation_alias="actual_cost_usd_total")
    estimated_cost_usd_total: float
    remaining_usd: float
    utilization_pct: float
    budget_exceeded: bool
    calls_total: int
    prompt_tokens_total: int
    completion_tokens_total: int

    model_config = ConfigDict(populate_by_name=True)


class BudgetHistoryResponse(BaseModel):
    generated_at: datetime
    days: int
    items: list[BudgetHistoryDay]
