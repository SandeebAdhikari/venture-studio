"""Persisted LLM budget threshold warnings."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LLMBudgetAlert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "llm_budget_alerts"

    budget_date: Mapped[date] = mapped_column(Date, nullable=False)
    threshold_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    spent_usd: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    budget_usd: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)

    __table_args__ = (
        UniqueConstraint("budget_date", "threshold_pct", name="uq_llm_budget_alerts_day_threshold"),
        Index("idx_llm_budget_alerts_date", "budget_date"),
    )
