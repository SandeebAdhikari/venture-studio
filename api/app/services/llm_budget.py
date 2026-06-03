"""LLM daily budget enforcement and reporting."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from app.agents.llm_cost import estimate_cost_usd
from app.config import Settings, get_settings
from app.exceptions import BudgetExceededError
from app.logging import get_logger
from app.repositories.llm_budget import LLMBudgetRepository

if TYPE_CHECKING:
    from app.repositories import RepositoryContainer

logger = get_logger(__name__)

BUDGET_WARNING_THRESHOLDS = (50, 75, 90)

DEFAULT_TOKEN_ESTIMATES: dict[str, tuple[int, int]] = {
    "classify_complaint": (1500, 400),
    "generate_opportunity": (3000, 1200),
    "research_market": (3500, 1400),
    "analyze_competitors": (3500, 1400),
    "research_customers": (3500, 1400),
    "validate_revenue": (3000, 1200),
    "plan_product_strategy": (3500, 1400),
    "plan_go_to_market": (3500, 1400),
    "evaluate_growth_strategy": (3500, 1400),
    "evaluate_human_proxy": (3000, 1200),
}

AGENT_DISPLAY_NAMES: dict[str, str] = {
    "classify_complaint": "Classification",
    "generate_opportunity": "Opportunity Generation",
    "research_market": "Market Research",
    "analyze_competitors": "Competitor Intelligence",
    "research_customers": "Customer Research",
    "validate_revenue": "Revenue Validation",
    "plan_product_strategy": "Product Strategy",
    "plan_go_to_market": "Go-To-Market",
    "evaluate_growth_strategy": "Growth Strategy",
    "evaluate_human_proxy": "Human Proxy",
}


class LLMBudgetService:
    """Tracks LLM spend, enforces daily caps, and emits threshold warnings."""

    def __init__(
        self,
        repos: RepositoryContainer,
        settings: Settings | None = None,
    ) -> None:
        self._repos = repos
        self._settings = settings or get_settings()
        self._metrics = LLMBudgetRepository(repos.session)

    @property
    def daily_budget_usd(self) -> float:
        return float(self._settings.llm_daily_budget_usd)

    @property
    def enabled(self) -> bool:
        return self.daily_budget_usd > 0

    def estimate_request_cost(
        self,
        graph_name: str,
        model: str,
        *,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> float:
        if prompt_tokens is None or completion_tokens is None:
            default_prompt, default_completion = DEFAULT_TOKEN_ESTIMATES.get(graph_name, (2500, 1000))
            prompt_tokens = default_prompt if prompt_tokens is None else prompt_tokens
            completion_tokens = default_completion if completion_tokens is None else completion_tokens
        return estimate_cost_usd(model, prompt_tokens, completion_tokens)

    async def get_daily_usage(self, day: date | None = None) -> dict[str, Any]:
        usage_day = day or self._metrics.utc_today()
        usage = await self._metrics.sum_usage_for_day(usage_day)
        budget = self.daily_budget_usd
        spent = usage["actual_cost_usd_total"]
        remaining = max(budget - spent, 0.0)
        utilization_pct = (spent / budget * 100.0) if budget > 0 else 0.0
        return {
            "usage_date": usage_day,
            "budget_usd": budget,
            "spent_usd": spent,
            "estimated_cost_usd_total": usage["estimated_cost_usd_total"],
            "remaining_usd": remaining,
            "utilization_pct": round(utilization_pct, 2),
            "calls_total": usage["calls_total"],
            "prompt_tokens_total": usage["prompt_tokens_total"],
            "completion_tokens_total": usage["completion_tokens_total"],
            "budget_exceeded": budget > 0 and spent >= budget,
        }

    async def get_usage_by_agent(self, day: date | None = None) -> list[dict[str, Any]]:
        usage_day = day or self._metrics.utc_today()
        rows = await self._metrics.usage_by_agent_for_day(usage_day)
        return [
            {
                **row,
                "display_name": AGENT_DISPLAY_NAMES.get(row["graph_name"], row["graph_name"]),
            }
            for row in rows
        ]

    async def get_status(self) -> dict[str, Any]:
        usage = await self.get_daily_usage()
        by_agent = await self.get_usage_by_agent()
        alerts = await self._metrics.list_alerts_for_day(usage["usage_date"])
        warnings = self._build_warnings(usage["utilization_pct"], alerts)
        return {
            **usage,
            "enabled": self.enabled,
            "warning_thresholds_pct": list(BUDGET_WARNING_THRESHOLDS),
            "warnings": warnings,
            "by_agent": by_agent,
        }

    async def get_history(self, *, days: int = 30) -> list[dict[str, Any]]:
        history = await self._metrics.daily_history(days=days)
        budget = self.daily_budget_usd
        return [
            {
                **row,
                "budget_usd": budget,
                "remaining_usd": max(budget - row["actual_cost_usd_total"], 0.0),
                "utilization_pct": round(
                    (row["actual_cost_usd_total"] / budget * 100.0) if budget > 0 else 0.0,
                    2,
                ),
                "budget_exceeded": budget > 0 and row["actual_cost_usd_total"] >= budget,
            }
            for row in history
        ]

    async def try_prepare_call(self, graph_name: str, model: str) -> tuple[float, str | None]:
        """Return pre-call estimate and optional budget block reason."""
        if not self.enabled:
            return 0.0, None

        estimated = self.estimate_request_cost(graph_name, model)
        try:
            await self.assert_can_spend(estimated, graph_name)
        except BudgetExceededError as exc:
            return estimated, f"budget_exceeded: {exc.message}"
        return estimated, None

    async def assert_can_spend(self, estimated_cost_usd: float, graph_name: str) -> None:
        if not self.enabled:
            return

        usage = await self.get_daily_usage()
        projected = usage["spent_usd"] + estimated_cost_usd
        if projected > self.daily_budget_usd:
            message = (
                f"Daily LLM budget exceeded for {graph_name}: "
                f"spent ${usage['spent_usd']:.4f}, "
                f"estimated next call ${estimated_cost_usd:.4f}, "
                f"budget ${self.daily_budget_usd:.2f}"
            )
            logger.warning(message, extra={"graph_name": graph_name, "projected_usd": projected})
            raise BudgetExceededError(
                message,
                spent_usd=usage["spent_usd"],
                budget_usd=self.daily_budget_usd,
            )

    async def after_call_recorded(self) -> None:
        if not self.enabled:
            return
        usage = await self.get_daily_usage()
        await self._record_threshold_alerts(
            usage_date=usage["usage_date"],
            spent_usd=usage["spent_usd"],
            utilization_pct=usage["utilization_pct"],
        )

    async def _record_threshold_alerts(
        self,
        *,
        usage_date: date,
        spent_usd: float,
        utilization_pct: float,
    ) -> None:
        for threshold in BUDGET_WARNING_THRESHOLDS:
            if utilization_pct < threshold:
                continue
            existing = await self._metrics.get_alert(usage_date, threshold)
            if existing is not None:
                continue
            await self._metrics.create_alert(
                budget_date=usage_date,
                threshold_pct=threshold,
                spent_usd=spent_usd,
                budget_usd=self.daily_budget_usd,
            )
            logger.warning(
                "LLM budget threshold reached",
                extra={
                    "threshold_pct": threshold,
                    "spent_usd": spent_usd,
                    "budget_usd": self.daily_budget_usd,
                },
            )

    @staticmethod
    def _build_warnings(utilization_pct: float, alerts: list[Any]) -> list[dict[str, Any]]:
        triggered = {alert.threshold_pct for alert in alerts}
        warnings: list[dict[str, Any]] = []
        for threshold in BUDGET_WARNING_THRESHOLDS:
            warnings.append(
                {
                    "threshold_pct": threshold,
                    "triggered": threshold in triggered or utilization_pct >= threshold,
                    "current_utilization_pct": utilization_pct,
                }
            )
        return warnings
