"""Unit tests for executive ranking engine."""

from uuid import uuid4

from app.ranking.engine import (
    ExecutiveRankingEngine,
    compute_competition_score,
    compute_founder_fit_score,
    compute_growth_score,
    compute_market_score,
    compute_pain_score,
    compute_revenue_score,
)
from app.ranking.schemas import AgentEvaluationInput, AgentSourceReferences


def test_compute_pain_score_uses_validation_readiness() -> None:
    score = compute_pain_score(
        pain_score=60,
        urgency_score=70,
        frequency_score=50,
        validation_readiness_score=88,
    )
    assert score == 88


def test_compute_market_score_from_sam_and_growth() -> None:
    score = compute_market_score(
        sam_usd=50_000_000,
        tam_usd=200_000_000,
        industry_growth_rate_pct=12,
        customer_segment_count=2,
    )
    assert score is not None
    assert 0 <= score <= 100


def test_compute_competition_score_prefers_differentiation() -> None:
    score = compute_competition_score(differentiation_score=0.8, threat_score=0.2)
    assert score == 80


def test_compute_revenue_score_blends_wtp_and_confidence() -> None:
    score = compute_revenue_score(
        willingness_to_pay_score=80,
        revenue_confidence_score=60,
        evaluation_readiness_score=None,
    )
    assert score == 73


def test_compute_growth_score_blends_growth_and_gtm() -> None:
    score = compute_growth_score(
        growth_readiness_score=75,
        growth_score=None,
        gtm_readiness_score=65,
    )
    assert score is not None
    assert 65 <= score <= 75


def test_compute_founder_fit_score_uses_ranking_score() -> None:
    score = compute_founder_fit_score(
        founder_fit_score=70,
        feasibility_score=60,
        planning_readiness_score=55,
        ranking_score=82,
    )
    assert score == 82


def test_engine_scores_weighted_final_from_all_dimensions() -> None:
    engine = ExecutiveRankingEngine()
    result = engine.score(
        AgentEvaluationInput(
            opportunity_id=uuid4(),
            opportunity_title="Scheduling SaaS",
            sources=AgentSourceReferences(),
            pain_score=80,
            market_score=70,
            revenue_score=75,
            competition_score=65,
            growth_score=72,
            founder_fit_score=85,
            agent_coverage_count=8,
        )
    )
    assert result is not None
    assert 0 < result.final_opportunity_score <= 100


def test_engine_returns_none_without_agent_coverage() -> None:
    engine = ExecutiveRankingEngine()
    result = engine.score(
        AgentEvaluationInput(
            opportunity_id=uuid4(),
            opportunity_title="Empty",
            agent_coverage_count=0,
        )
    )
    assert result is None
