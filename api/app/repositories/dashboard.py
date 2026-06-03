"""Aggregate queries for dashboard metrics."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ReviewStatus, SignalProcessingStatus
from app.db.models.competitor_analysis import CompetitorAnalysis
from app.db.models.complaint import Complaint
from app.db.models.customer_research import CustomerResearch
from app.db.models.growth_evaluation import GrowthEvaluation
from app.db.models.gtm_plan import GTMPlan
from app.db.models.human_proxy_evaluation import HumanProxyEvaluation
from app.db.models.llm_call import LLMCall
from app.db.models.market_brief import MarketBrief
from app.db.models.opportunity import Opportunity
from app.db.models.product_strategy import ProductStrategy
from app.db.models.revenue_validation import RevenueValidation
from app.db.models.signal import Signal
from app.db.models.source import Source


class DashboardMetricsRepository:
    """Read-only aggregate queries for dashboard endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_signals_by_status(self) -> dict[str, int]:
        result = await self.session.execute(
            select(Signal.processing_status, func.count())
            .select_from(Signal)
            .group_by(Signal.processing_status)
        )
        return {status: int(count) for status, count in result.all()}

    async def count_opportunities_by_review_status(self) -> dict[str, int]:
        result = await self.session.execute(
            select(Opportunity.review_status, func.count())
            .select_from(Opportunity)
            .group_by(Opportunity.review_status)
        )
        return {status: int(count) for status, count in result.all()}

    async def count_enabled_sources(self) -> int:
        result = await self.session.scalar(
            select(func.count())
            .select_from(Source)
            .where(Source.enabled.is_(True))
        )
        return int(result or 0)

    async def count_complaints(self) -> int:
        result = await self.session.scalar(select(func.count()).select_from(Complaint))
        return int(result or 0)

    async def count_opportunities(self) -> int:
        result = await self.session.scalar(select(func.count()).select_from(Opportunity))
        return int(result or 0)

    async def llm_metrics(self, *, since: datetime | None = None) -> dict[str, Any]:
        query = select(
            func.count(),
            func.coalesce(func.sum(LLMCall.cost_usd), 0),
            func.coalesce(func.sum(LLMCall.prompt_tokens), 0),
            func.coalesce(func.sum(LLMCall.completion_tokens), 0),
        ).select_from(LLMCall)
        if since is not None:
            query = query.where(LLMCall.created_at >= since)
        result = await self.session.execute(query)
        total, cost, prompt_tokens, completion_tokens = result.one()
        return {
            "calls_total": int(total or 0),
            "cost_usd_total": float(cost or 0),
            "prompt_tokens_total": int(prompt_tokens or 0),
            "completion_tokens_total": int(completion_tokens or 0),
        }

    async def agent_current_status_counts(
        self,
        model: Any,
        *,
        agent_key: str,
        display_name: str,
    ) -> dict[str, Any]:
        result = await self.session.execute(
            select(model.status, func.count())
            .select_from(model)
            .where(model.is_current.is_(True))
            .group_by(model.status)
        )
        by_status = {status: int(count) for status, count in result.all()}
        return {
            "agent": agent_key,
            "display_name": display_name,
            "current_completed": by_status.get("completed", 0),
            "current_failed": by_status.get("failed", 0),
            "current_skipped": by_status.get("skipped", 0),
            "current_total": sum(by_status.values()),
        }

    async def all_agent_statuses(self) -> list[dict[str, Any]]:
        agents = [
            (MarketBrief, "market_research", "Market Research"),
            (CompetitorAnalysis, "competitor_analysis", "Competitor Analysis"),
            (CustomerResearch, "customer_research", "Customer Research"),
            (RevenueValidation, "revenue_validation", "Revenue Validation"),
            (ProductStrategy, "product_strategy", "Product Strategy"),
            (GTMPlan, "go_to_market", "Go-To-Market"),
            (GrowthEvaluation, "growth_strategy", "Growth Strategy"),
            (HumanProxyEvaluation, "human_proxy", "Human Proxy"),
        ]
        statuses: list[dict[str, Any]] = []
        for model, key, display_name in agents:
            statuses.append(
                await self.agent_current_status_counts(model, agent_key=key, display_name=display_name)
            )
        return statuses

    async def average_agent_coverage(self) -> float | None:
        from app.db.models.executive_ranking_entry import ExecutiveRankingEntry
        from app.db.models.executive_ranking_run import ExecutiveRankingRun

        result = await self.session.scalar(
            select(func.avg(ExecutiveRankingEntry.agent_coverage_count))
            .select_from(ExecutiveRankingEntry)
            .join(
                ExecutiveRankingRun,
                ExecutiveRankingEntry.executive_ranking_run_id == ExecutiveRankingRun.id,
            )
            .where(ExecutiveRankingRun.is_current.is_(True))
        )
        if result is None:
            return None
        return round(float(result), 2)

    @staticmethod
    def signal_status_map(raw: dict[str, int]) -> dict[str, int]:
        return {
            "pending": raw.get(SignalProcessingStatus.PENDING.value, 0),
            "classified": raw.get(SignalProcessingStatus.CLASSIFIED.value, 0),
            "failed": raw.get(SignalProcessingStatus.FAILED.value, 0),
            "skipped": raw.get(SignalProcessingStatus.SKIPPED.value, 0),
            "processing": raw.get(SignalProcessingStatus.PROCESSING.value, 0),
        }

    @staticmethod
    def review_status_map(raw: dict[str, int]) -> dict[str, int]:
        return {
            status.value: raw.get(status.value, 0)
            for status in ReviewStatus
        }

    async def collection_metrics(self) -> dict[str, int]:
        signal_counts = self.signal_status_map(await self.count_signals_by_status())
        total_signals = sum(signal_counts.values())
        return {
            "signals_total": total_signals,
            "signals_pending": signal_counts["pending"] + signal_counts["processing"],
            "signals_classified": signal_counts["classified"],
            "signals_failed": signal_counts["failed"],
            "signals_skipped": signal_counts["skipped"],
            "complaints_total": await self.count_complaints(),
            "sources_enabled": await self.count_enabled_sources(),
        }

    async def classification_metrics(self) -> dict[str, Any]:
        signal_counts = self.signal_status_map(await self.count_signals_by_status())
        llm_all = await self.llm_metrics()
        return {
            **signal_counts,
            "complaints_total": await self.count_complaints(),
            **llm_all,
        }

    async def research_metrics(self) -> dict[str, Any]:
        return {
            "opportunities_total": await self.count_opportunities(),
            "agents": await self.all_agent_statuses(),
            "average_agent_coverage": await self.average_agent_coverage(),
        }
