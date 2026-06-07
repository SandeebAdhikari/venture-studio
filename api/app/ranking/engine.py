"""Deterministic executive ranking engine."""

from __future__ import annotations

import math

from app.ranking.constants import DEFAULT_DIMENSION_WEIGHTS, RANKING_ENGINE
from app.ranking.schemas import (
    AgentEvaluationInput,
    ExecutiveComponentScores,
    ExecutiveRankingScore,
)

__all__ = ["ExecutiveRankingEngine", "RANKING_ENGINE"]


class ExecutiveRankingEngine:
    """Combines agent outputs into composite opportunity scores."""

    def __init__(
        self,
        *,
        dimension_weights: dict[str, float] | None = None,
    ) -> None:
        self._weights = dimension_weights or DEFAULT_DIMENSION_WEIGHTS

    def score(self, data: AgentEvaluationInput) -> ExecutiveRankingScore | None:
        if data.agent_coverage_count <= 0:
            return None

        components = ExecutiveComponentScores(
            pain_score=data.pain_score,
            market_score=data.market_score,
            revenue_score=data.revenue_score,
            competition_score=data.competition_score,
            growth_score=data.growth_score,
            founder_fit_score=data.founder_fit_score,
        )

        final_score = self._weighted_final(components)
        if final_score is None:
            return None

        return ExecutiveRankingScore(
            opportunity_id=data.opportunity_id,
            opportunity_title=data.opportunity_title,
            final_opportunity_score=final_score,
            components=components,
            agent_coverage_count=data.agent_coverage_count,
            source_references=data.sources,
            ranking_details={
                **data.ranking_details,
                "dimension_weights": self._weights,
                "engine": RANKING_ENGINE,
            },
        )

    def _weighted_final(self, components: ExecutiveComponentScores) -> int | None:
        dimension_values = {
            "pain": components.pain_score,
            "market": components.market_score,
            "revenue": components.revenue_score,
            "competition": components.competition_score,
            "growth": components.growth_score,
            "founder_fit": components.founder_fit_score,
        }

        available = {key: value for key, value in dimension_values.items() if value is not None}
        if not available:
            return None

        weight_total = sum(self._weights[key] for key in available)
        weighted = sum(
            (self._weights[key] / weight_total) * value for key, value in available.items()
        )
        return int(round(min(100.0, max(0.0, weighted))))


def compute_market_score(
    *,
    sam_usd: float | None,
    tam_usd: float | None,
    industry_growth_rate_pct: float | None,
    customer_segment_count: int,
) -> int | None:
    parts: list[int] = []

    market_usd = sam_usd or tam_usd
    if market_usd is not None and market_usd > 0:
        log_score = min(100, int(round(math.log10(max(market_usd, 1)) * 18)))
        parts.append(max(20, log_score))

    if industry_growth_rate_pct is not None:
        growth_score = min(100, max(0, int(50 + industry_growth_rate_pct * 2)))
        parts.append(growth_score)

    if customer_segment_count > 0:
        parts.append(min(100, 35 + customer_segment_count * 12))

    if not parts:
        return None
    return int(round(sum(parts) / len(parts)))


def compute_competition_score(
    *,
    differentiation_score: float | None,
    threat_score: float | None,
) -> int | None:
    if differentiation_score is None and threat_score is None:
        return None

    diff = differentiation_score if differentiation_score is not None else 0.5
    threat = threat_score if threat_score is not None else 0.5
    composite = (diff * 0.7) + ((1.0 - threat) * 0.3)
    return int(round(min(100.0, max(0.0, composite * 100))))


def compute_pain_score(
    *,
    pain_score: int | None,
    urgency_score: int | None,
    frequency_score: int | None,
    validation_readiness_score: int | None,
) -> int | None:
    if validation_readiness_score is not None:
        return validation_readiness_score

    parts = [score for score in (pain_score, urgency_score, frequency_score) if score is not None]
    if not parts:
        return None

    if pain_score is not None and urgency_score is not None and frequency_score is not None:
        return int(round(pain_score * 0.5 + urgency_score * 0.25 + frequency_score * 0.25))

    return int(round(sum(parts) / len(parts)))


def compute_revenue_score(
    *,
    willingness_to_pay_score: int | None,
    revenue_confidence_score: int | None,
    evaluation_readiness_score: int | None,
) -> int | None:
    if evaluation_readiness_score is not None:
        return evaluation_readiness_score

    if willingness_to_pay_score is None and revenue_confidence_score is None:
        return None

    wtp = willingness_to_pay_score if willingness_to_pay_score is not None else 50
    confidence = revenue_confidence_score if revenue_confidence_score is not None else 50
    return int(round(wtp * 0.65 + confidence * 0.35))


def compute_growth_score(
    *,
    growth_readiness_score: int | None,
    growth_score: int | None,
    gtm_readiness_score: int | None,
) -> int | None:
    parts: list[tuple[int, float]] = []
    if growth_readiness_score is not None:
        parts.append((growth_readiness_score, 0.55))
    elif growth_score is not None:
        parts.append((growth_score, 0.45))

    if gtm_readiness_score is not None:
        parts.append((gtm_readiness_score, 0.45 if growth_readiness_score is not None else 0.55))

    if not parts:
        return None

    weight_total = sum(weight for _, weight in parts)
    composite = sum(value * (weight / weight_total) for value, weight in parts)
    return int(round(composite))


def compute_founder_fit_score(
    *,
    founder_fit_score: int | None,
    feasibility_score: int | None,
    planning_readiness_score: int | None,
    ranking_score: int | None,
) -> int | None:
    has_fit_inputs = founder_fit_score is not None and feasibility_score is not None

    if has_fit_inputs:
        base = int(round(founder_fit_score * 0.70 + feasibility_score * 0.30))
    elif ranking_score is not None:
        base = ranking_score
    elif founder_fit_score is not None:
        fit = founder_fit_score
        feasibility = feasibility_score if feasibility_score is not None else fit
        base = int(round(fit * 0.7 + feasibility * 0.3))
    elif planning_readiness_score is not None:
        base = planning_readiness_score
    else:
        return None

    if planning_readiness_score is not None and ranking_score is None:
        return int(round(base * 0.85 + planning_readiness_score * 0.15))
    return base


def build_founder_fit_ranking_details(
    *,
    founder_fit_score: int | None,
    feasibility_score: int | None,
    executive_founder_fit: int | None,
) -> dict[str, object]:
    if (
        executive_founder_fit is None
        or founder_fit_score is None
        or feasibility_score is None
    ):
        return {}

    return {
        "founder_fit_source": "human_proxy_v1",
        "founder_fit_score": founder_fit_score,
        "feasibility_score": feasibility_score,
        "executive_founder_fit": executive_founder_fit,
    }
