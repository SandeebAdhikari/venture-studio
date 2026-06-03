"""Unit tests for opportunity score computation."""

from uuid import uuid4

from app.agents.opportunity.schemas import ComplaintPattern
from app.agents.opportunity.scoring import compute_opportunity_scores


def test_compute_scores_for_large_pattern() -> None:
    pattern = ComplaintPattern(
        topic="Staff Scheduling",
        complaint_ids=[uuid4() for _ in range(100)],
        domain_code="saas_b2b",
        category_code="workflow",
        dominant_persona_code="ops_admin",
        complaint_count=100,
        avg_severity=4.0,
    )
    scores = compute_opportunity_scores(
        pattern,
        confidence_score=0.9,
        min_cluster_size=3,
    )
    assert scores["frequency_score"] == 1.0
    assert scores["severity_score"] == 0.8
    assert scores["overall_score"] > 0.8
