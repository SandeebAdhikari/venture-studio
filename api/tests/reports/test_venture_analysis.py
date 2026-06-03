"""Unit tests for venture report analysis helpers."""

from app.reports.venture.analysis import (
    RECOMMEND_EXPLORE,
    RECOMMEND_PURSUE,
    build_recommendation,
    build_risk_items,
    format_risk_analysis_markdown,
)


def test_build_recommendation_pursue_for_high_scores() -> None:
    result = build_recommendation(
        final_score=82,
        human_proxy_recommendation="pursue",
        pain_score=88,
        founder_fit_score=85,
        rank=1,
    )
    assert RECOMMEND_PURSUE.split("—")[0].strip() in result
    assert "Ranked #1" in result
    assert "82/100" in result


def test_build_recommendation_pass_when_proxy_says_pass() -> None:
    result = build_recommendation(
        final_score=70,
        human_proxy_recommendation="pass",
        pain_score=60,
        founder_fit_score=40,
        rank=3,
    )
    assert "Pass" in result


def test_build_recommendation_explore_for_moderate_score() -> None:
    result = build_recommendation(
        final_score=58,
        human_proxy_recommendation="explore",
        pain_score=62,
        founder_fit_score=55,
        rank=2,
    )
    assert RECOMMEND_EXPLORE.split("—")[0].strip() in result


def test_build_risk_items_includes_growth_and_competition() -> None:
    risks = build_risk_items(
        growth_risk_score=78,
        technical_risks=[{"risk": "Complex integrations", "severity": "high"}],
        execution_complexity={"complexity_level": "high", "rationale": "Heavy ops load."},
        capital_requirements={"bootstrap_friendly": False, "rationale": "Needs paid ads."},
        competitor_threat_level="high",
        revenue_confidence_score=40,
    )
    categories = {risk.category for risk in risks}
    assert "growth" in categories
    assert "competition" in categories
    assert "product" in categories
    assert "capital" in categories


def test_build_risk_items_defaults_when_no_signals() -> None:
    risks = build_risk_items(
        growth_risk_score=None,
        technical_risks=[],
        execution_complexity=None,
        capital_requirements=None,
        competitor_threat_level=None,
        revenue_confidence_score=None,
    )
    assert len(risks) == 1
    assert risks[0].severity == "low"


def test_format_risk_analysis_markdown() -> None:
    risks = build_risk_items(
        growth_risk_score=80,
        technical_risks=[],
        execution_complexity=None,
        capital_requirements=None,
        competitor_threat_level="medium",
        revenue_confidence_score=None,
    )
    markdown = format_risk_analysis_markdown(risks)
    assert "**Growth" in markdown
    assert "**Competition" in markdown
