"""Collector integration tests for venture report readability."""

from uuid import uuid4

import pytest

from app.reports.venture.collector import VentureReportCollector
from app.reports.venture.schemas import CustomerEvidenceItem
from app.schemas.executive_ranking import ExecutiveRankingEntryRead


class _FakeProfile:
    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeCompetitor:
    executive_summary = "Landscape reviewed."
    evaluation_metrics = {"competitor_count": 2, "differentiation_score": 0.63, "threat_level": "low"}
    profiles = [
        _FakeProfile(
            name="Docker",
            positioning="Containers",
            sentiment_score=-0.3,
            strengths=["Ecosystem"],
            weaknesses=["Complexity"],
        )
    ]
    competitive_gaps = [{"gap": "Simpler onboarding", "description": "Faster first-run setup."}]


class _FakeProduct:
    executive_summary = "MVP plan ready."
    mvp_definition = "Automate dev environment setup."
    estimated_timeline = {"mvp_weeks": 6}
    core_features = [{"name": "Auto setup"}]
    roadmap = [
        {
            "phase_name": "Phase 1: Design",
            "start_week": 1,
            "end_week": 2,
            "duration_weeks": 2,
            "milestones": ["Wireframes"],
            "deliverables": ["Specs"],
        }
    ]
    development_phases = []


class _FakeGtm:
    gtm_report = "Community-led launch."
    confidence_score = 85
    estimated_cac_usd = 50
    customer_personas = [
        {
            "persona_name": "Full-Stack Developer",
            "role": "Engineer",
            "pain_points": ["Setup time"],
            "goals": ["Ship faster"],
            "preferred_channels": ["Forums"],
        }
    ]
    acquisition_channels = [
        {
            "channel_name": "Developer Forums",
            "priority": "primary",
            "channel_type": "community",
            "estimated_cac_usd": 50,
            "rationale": "Meet users where they complain.",
        }
    ]


class _FakeGrowth:
    executive_summary = "SEO and partnerships."
    growth_score = 85
    scalability_score = 80
    risk_score = 30
    evaluation_metrics = {"growth_readiness_score": 80}
    growth_roadmap = [
        {
            "phase_name": "Awareness",
            "start_month": 1,
            "end_month": 6,
            "focus": "Content",
            "growth_levers": ["SEO"],
            "milestones": ["Launch blog"],
        }
    ]


class _FakeHumanProxy:
    executive_summary = "Technically aligned solo build."
    founder_fit_score = 8
    feasibility_score = 7
    recommendation = "explore"
    founder_fit_analysis = {"skill_matches": ["Python"], "skill_gaps": []}
    implementation_feasibility = {"build_complexity": "medium"}
    learning_curve = {"difficulty": "medium"}


def test_collector_sections_avoid_raw_dicts_and_align_scores() -> None:
    collector = VentureReportCollector(repos=None)  # type: ignore[arg-type]

    mvp = collector._mvp_plan(_FakeProduct())
    gtm = collector._gtm_strategy(_FakeGtm())
    growth = collector._growth_strategy(_FakeGrowth())
    founder = collector._founder_fit_analysis(
        _FakeHumanProxy(),
        ranking_founder_fit_score=24,
    )
    competitor = collector._competitor_analysis(_FakeCompetitor())

    for section in (mvp, gtm, growth, founder, competitor):
        assert "{" not in section
        assert "}" not in section

    assert "Phase 1: Design" in mvp
    assert "Full-Stack Developer" in gtm
    assert "Awareness" in growth
    assert "executive ranking" in founder.lower()
    assert "80/100" in founder
    assert "63/100" in competitor
    assert "Where you can win" in competitor
