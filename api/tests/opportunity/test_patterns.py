"""Unit tests for topic pattern detection."""

from uuid import uuid4

from app.agents.opportunity.patterns import TopicPatternDetector
from app.agents.opportunity.schemas import ComplaintEvidence


def _complaint(summary: str, *, severity: int = 4) -> ComplaintEvidence:
    return ComplaintEvidence(
        id=uuid4(),
        summary=summary,
        verbatim_quote=summary[:40],
        severity=severity,
        domain_code="saas_b2b",
        category_code="workflow",
        persona_code="ops_admin",
        product_mentions=[],
    )


def test_detects_staff_scheduling_pattern() -> None:
    complaints = [
        _complaint("Staff scheduling breaks every week when staff call out sick.")
        for _ in range(5)
    ]
    complaints.append(
        _complaint("Pricing is unrelated and should not dominate the batch.", severity=2)
    )

    patterns = TopicPatternDetector().detect(complaints, min_cluster_size=3)

    assert len(patterns) >= 1
    assert any(pattern.complaint_count >= 3 for pattern in patterns)


def test_returns_empty_when_below_min_cluster_size() -> None:
    complaints = [
        _complaint("Staff scheduling is hard."),
        _complaint("Staff scheduling fails on weekends."),
    ]
    patterns = TopicPatternDetector().detect(complaints, min_cluster_size=3)
    assert patterns == []
