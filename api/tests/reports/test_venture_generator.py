"""Unit tests for venture report markdown generation."""

from datetime import UTC, datetime
from uuid import uuid4

from app.reports.venture.generator import VentureReportGenerator
from app.reports.venture.schemas import CustomerEvidenceItem, RiskItem, VentureOpportunityReport


def _report(**overrides) -> VentureOpportunityReport:
    payload = {
        "rank": 1,
        "opportunity_id": uuid4(),
        "title": "Staff Scheduling SaaS",
        "final_opportunity_score": 84,
        "pain_score": 88,
        "market_score": 72,
        "revenue_score": 76,
        "competition_score": 68,
        "growth_score": 74,
        "founder_fit_score": 85,
        "opportunity_summary": "**Problem:** Teams struggle with scheduling.",
        "market_analysis": "Large SAM with steady growth.",
        "competitor_analysis": "Differentiation opportunity against incumbents.",
        "customer_evidence": [
            CustomerEvidenceItem(
                summary="Scheduling chaos every week.",
                verbatim_quote="Scheduling chaos every week.",
                severity=5,
                source_url="https://example.com/post/1",
            )
        ],
        "revenue_analysis": "Buyers show willingness to pay.",
        "mvp_plan": "MVP in 8 weeks with core scheduling workflow.",
        "go_to_market_strategy": "Founder-led outbound to ops admins.",
        "growth_strategy": "Expand through referrals and SEO.",
        "founder_fit_analysis": "Strong fit for a solo technical founder.",
        "risk_analysis": [
            RiskItem(
                category="execution",
                severity="medium",
                description="Moderate operational support load.",
            )
        ],
        "recommendation": "Pursue — strong composite score with validated demand and founder fit.",
    }
    payload.update(overrides)
    return VentureOpportunityReport(**payload)


def test_render_markdown_includes_all_sections() -> None:
    generator = VentureReportGenerator()
    markdown = generator.render_markdown(
        [_report()],
        generated_at=datetime(2026, 6, 3, 12, 0, tzinfo=UTC),
    )

    assert "# Venture Recommendation Report" in markdown
    assert "## 1. Staff Scheduling SaaS" in markdown
    assert "### Market analysis" in markdown
    assert "### Competitor analysis" in markdown
    assert "### Customer evidence" in markdown
    assert "### Revenue analysis" in markdown
    assert "### MVP plan" in markdown
    assert "### Go-to-market strategy" in markdown
    assert "### Growth strategy" in markdown
    assert "### Founder fit analysis" in markdown
    assert "### Risk analysis" in markdown
    assert "### Recommendation" in markdown
    assert "Scheduling chaos every week." in markdown
    assert "https://example.com/post/1" in markdown


def test_build_report_structures_content() -> None:
    generator = VentureReportGenerator()
    content = generator.build_report([_report()])

    assert content.generated_count == 1
    assert len(content.opportunities) == 1
    assert "Venture Recommendation Report" in content.markdown
