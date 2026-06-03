"""Unit tests for opportunity scoring engine."""

from uuid import uuid4

from app.scoring.engine import OpportunityScoringEngine
from app.scoring.schemas import ScoringInput


def _input(**overrides) -> ScoringInput:
    payload = {
        "opportunity_id": uuid4(),
        "confidence_score": 0.85,
        "complaint_count": 100,
        "avg_severity": 4.0,
        "max_severity": 5,
        "domain_code": "devtools",
        "category_code": "workflow",
        "dominant_persona_code": "founder",
        "unique_product_count": 4,
        "has_documented_alternatives": True,
        "gap_text": "No lightweight workflow exists for this use case in evidence.",
    }
    payload.update(overrides)
    return ScoringInput(**payload)


def test_high_volume_complaints_increase_score() -> None:
    engine = OpportunityScoringEngine(volume_target=50)
    high = engine.score(_input(complaint_count=100))
    low = engine.score(_input(complaint_count=2))

    assert high.score > low.score
    assert high.dimensions.volume == 100
    assert low.dimensions.volume < 20


def test_severity_affects_score() -> None:
    engine = OpportunityScoringEngine()
    high = engine.score(_input(avg_severity=5.0, max_severity=5))
    low = engine.score(_input(avg_severity=1.5, max_severity=2))

    assert high.dimensions.severity > low.dimensions.severity
    assert high.score > low.score


def test_founder_fit_prefers_devtools_and_founder_persona() -> None:
    engine = OpportunityScoringEngine()
    fit = engine.score(
        _input(domain_code="devtools", dominant_persona_code="founder", category_code="workflow")
    )
    poor = engine.score(
        _input(
            domain_code="healthcare",
            dominant_persona_code="consumer",
            category_code="security",
        )
    )

    assert fit.dimensions.founder_fit > poor.dimensions.founder_fit


def test_score_is_bounded_0_to_100() -> None:
    engine = OpportunityScoringEngine()
    result = engine.score(_input())
    assert 0 <= result.score <= 100
