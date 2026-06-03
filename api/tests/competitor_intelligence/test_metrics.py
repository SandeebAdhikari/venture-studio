"""Unit tests for competitor analysis metrics."""

from app.agents.competitor_intelligence.metrics import compute_evaluation_metrics
from app.agents.competitor_intelligence.mock_client import default_mock_competitor_output


def test_compute_evaluation_metrics_from_default_mock() -> None:
    output = default_mock_competitor_output()
    metrics = compute_evaluation_metrics(output)

    assert metrics["competitor_count"] == 2
    assert metrics["competitive_gap_count"] == 1
    assert metrics["threat_level"] in {"low", "medium", "high"}
    assert 0.0 <= metrics["threat_score"] <= 1.0
    assert 0.0 <= metrics["differentiation_score"] <= 1.0
    assert metrics["pricing_transparency_score"] > 0.0
