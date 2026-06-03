"""Unit tests for executive report markdown generation."""

from datetime import UTC, datetime
from uuid import uuid4

from app.reports.executive.generator import (
    RECOMMEND_EXPLORE,
    RECOMMEND_PRIORITIZE,
    ExecutiveReportGenerator,
)
from app.reports.executive.schemas import KeyComplaintEntry, TopOpportunityEntry


def _entry(**overrides) -> TopOpportunityEntry:
    complaint = KeyComplaintEntry(
        id=uuid4(),
        summary="Staff scheduling is chaotic for managers.",
        verbatim_quote="Staff scheduling breaks every week.",
        severity=4,
        source_url="https://example.com/post/1",
    )
    payload = {
        "opportunity_id": uuid4(),
        "title": "Staff Scheduling SaaS",
        "score": 82,
        "confidence": 0.86,
        "recommendation": RECOMMEND_PRIORITIZE,
        "supporting_evidence_count": 3,
        "supporting_evidence": [complaint],
        "key_complaints": [complaint],
        "problem_statement": "Teams struggle to coordinate hourly staff schedules.",
        "frequency_signal": "Multiple complaints mention staff scheduling pain.",
        "gap": "No lightweight scheduling workflow for small teams.",
    }
    payload.update(overrides)
    return TopOpportunityEntry(**payload)


def test_recommend_prioritize_for_high_score_and_confidence() -> None:
    generator = ExecutiveReportGenerator()
    assert generator.recommend(score=80, confidence=0.75) == RECOMMEND_PRIORITIZE


def test_recommend_explore_for_moderate_score() -> None:
    generator = ExecutiveReportGenerator()
    assert generator.recommend(score=60, confidence=0.55) == RECOMMEND_EXPLORE


def test_render_markdown_includes_required_fields() -> None:
    generator = ExecutiveReportGenerator()
    entry = _entry()
    markdown = generator.render_markdown(
        [entry],
        generated_at=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
    )

    assert "# Top Opportunities Report" in markdown
    assert "Staff Scheduling SaaS" in markdown
    assert "**Score:** 82/100" in markdown
    assert "**Confidence:** 86%" in markdown
    assert RECOMMEND_PRIORITIZE in markdown
    assert "Staff scheduling is chaotic for managers." in markdown
    assert "https://example.com/post/1" in markdown
