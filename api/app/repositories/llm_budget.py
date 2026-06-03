"""LLM budget aggregation and alert persistence."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.llm_budget_alert import LLMBudgetAlert
from app.db.models.llm_call import LLMCall


class LLMBudgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def utc_day_bounds(day: date) -> tuple[datetime, datetime]:
        start = datetime.combine(day, time.min, tzinfo=UTC)
        return start, start + timedelta(days=1)

    @staticmethod
    def utc_today() -> date:
        return datetime.now(UTC).date()

    async def sum_usage_for_day(self, day: date) -> dict[str, Any]:
        start, end = self.utc_day_bounds(day)
        result = await self.session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(LLMCall.prompt_tokens), 0),
                func.coalesce(func.sum(LLMCall.completion_tokens), 0),
                func.coalesce(func.sum(LLMCall.estimated_cost_usd), 0),
                func.coalesce(func.sum(LLMCall.cost_usd), 0),
            )
            .select_from(LLMCall)
            .where(LLMCall.created_at >= start, LLMCall.created_at < end)
        )
        total_calls, prompt_tokens, completion_tokens, estimated_cost, actual_cost = result.one()
        return {
            "calls_total": int(total_calls or 0),
            "prompt_tokens_total": int(prompt_tokens or 0),
            "completion_tokens_total": int(completion_tokens or 0),
            "estimated_cost_usd_total": float(estimated_cost or 0),
            "actual_cost_usd_total": float(actual_cost or 0),
        }

    async def usage_by_agent_for_day(self, day: date) -> list[dict[str, Any]]:
        start, end = self.utc_day_bounds(day)
        result = await self.session.execute(
            select(
                LLMCall.graph_name,
                func.count(),
                func.coalesce(func.sum(LLMCall.prompt_tokens), 0),
                func.coalesce(func.sum(LLMCall.completion_tokens), 0),
                func.coalesce(func.sum(LLMCall.estimated_cost_usd), 0),
                func.coalesce(func.sum(LLMCall.cost_usd), 0),
            )
            .select_from(LLMCall)
            .where(LLMCall.created_at >= start, LLMCall.created_at < end)
            .group_by(LLMCall.graph_name)
            .order_by(func.coalesce(func.sum(LLMCall.cost_usd), 0).desc())
        )
        return [
            {
                "graph_name": graph_name,
                "calls_total": int(calls or 0),
                "prompt_tokens_total": int(prompt_tokens or 0),
                "completion_tokens_total": int(completion_tokens or 0),
                "estimated_cost_usd_total": float(estimated_cost or 0),
                "actual_cost_usd_total": float(actual_cost or 0),
            }
            for graph_name, calls, prompt_tokens, completion_tokens, estimated_cost, actual_cost in result.all()
        ]

    async def daily_history(self, *, days: int) -> list[dict[str, Any]]:
        today = self.utc_today()
        start_day = today - timedelta(days=max(days - 1, 0))
        start, _ = self.utc_day_bounds(start_day)

        day_column = cast(func.date_trunc("day", LLMCall.created_at), Date).label("usage_date")
        result = await self.session.execute(
            select(
                day_column,
                func.count(),
                func.coalesce(func.sum(LLMCall.prompt_tokens), 0),
                func.coalesce(func.sum(LLMCall.completion_tokens), 0),
                func.coalesce(func.sum(LLMCall.estimated_cost_usd), 0),
                func.coalesce(func.sum(LLMCall.cost_usd), 0),
            )
            .select_from(LLMCall)
            .where(LLMCall.created_at >= start)
            .group_by(day_column)
            .order_by(day_column.desc())
        )
        return [
            {
                "usage_date": usage_date,
                "calls_total": int(calls or 0),
                "prompt_tokens_total": int(prompt_tokens or 0),
                "completion_tokens_total": int(completion_tokens or 0),
                "estimated_cost_usd_total": float(estimated_cost or 0),
                "actual_cost_usd_total": float(actual_cost or 0),
            }
            for usage_date, calls, prompt_tokens, completion_tokens, estimated_cost, actual_cost in result.all()
        ]

    async def list_alerts_for_day(self, day: date) -> list[LLMBudgetAlert]:
        result = await self.session.execute(
            select(LLMBudgetAlert)
            .where(LLMBudgetAlert.budget_date == day)
            .order_by(LLMBudgetAlert.threshold_pct.asc())
        )
        return list(result.scalars().all())

    async def get_alert(self, day: date, threshold_pct: int) -> LLMBudgetAlert | None:
        return await self.session.scalar(
            select(LLMBudgetAlert).where(
                LLMBudgetAlert.budget_date == day,
                LLMBudgetAlert.threshold_pct == threshold_pct,
            )
        )

    async def create_alert(
        self,
        *,
        budget_date: date,
        threshold_pct: int,
        spent_usd: float,
        budget_usd: float,
    ) -> LLMBudgetAlert:
        alert = LLMBudgetAlert(
            budget_date=budget_date,
            threshold_pct=threshold_pct,
            spent_usd=spent_usd,
            budget_usd=budget_usd,
        )
        self.session.add(alert)
        await self.session.flush()
        return alert
