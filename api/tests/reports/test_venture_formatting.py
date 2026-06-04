"""Tests for venture report markdown formatting helpers."""

from app.reports.venture.formatting import (
    format_acquisition_channel,
    format_bullet_list,
    format_differentiation_score,
    format_growth_phase,
    format_persona,
    format_roadmap_phase,
    format_structured_bullet,
    market_size_disclaimer,
    normalize_century_score,
)


def test_normalize_century_score_scales_zero_to_ten() -> None:
    assert normalize_century_score(8) == 80
    assert normalize_century_score(85) == 85


def test_format_structured_bullet_avoids_raw_dict_for_roadmap() -> None:
    phase = {
        "phase_name": "Phase 1: Research and Design",
        "start_week": 1,
        "end_week": 2,
        "duration_weeks": 2,
        "milestones": ["Complete user research"],
        "deliverables": ["Wireframes"],
    }
    rendered = format_structured_bullet(phase)
    assert "Phase 1: Research and Design" in rendered
    assert "weeks 1–2" in rendered
    assert "{" not in rendered


def test_format_persona_and_channel_readable() -> None:
    persona = {
        "persona_name": "Full-Stack Developer",
        "role": "Software Engineer",
        "pain_points": ["Complex setup"],
        "goals": ["Ship faster"],
        "preferred_channels": ["Forums"],
    }
    channel = {
        "channel_name": "Developer Forums",
        "priority": "primary",
        "channel_type": "community",
        "estimated_cac_usd": 50.0,
        "rationale": "Organic discovery.",
    }
    assert "Full-Stack Developer" in format_persona(persona)
    assert "Developer Forums" in format_acquisition_channel(channel)
    assert "{" not in format_persona(persona)


def test_format_growth_phase_readable() -> None:
    phase = {
        "phase_name": "Market Awareness",
        "start_month": 1,
        "end_month": 6,
        "focus": "Content marketing",
        "growth_levers": ["SEO"],
    }
    rendered = format_growth_phase(phase)
    assert "Market Awareness" in rendered
    assert "months 1–6" in rendered


def test_format_bullet_list_no_python_dict_leak() -> None:
    items = [
        {"phase_name": "MVP Development", "start_week": 3, "end_week": 8, "duration_weeks": 6},
        {"persona_name": "DevOps Engineer", "role": "SRE", "pain_points": ["Deploy pain"]},
    ]
    markdown = format_bullet_list(items)
    assert "MVP Development" in markdown
    assert "DevOps Engineer" in markdown
    assert "{" not in markdown


def test_format_differentiation_score_fraction_to_percent() -> None:
    assert format_differentiation_score(0.63) == "63/100"


def test_market_disclaimer_reflects_evidence() -> None:
    assert "no linked citations" in market_size_disclaimer(has_evidence=False).lower()
    assert "supporting evidence" in market_size_disclaimer(has_evidence=True).lower()
