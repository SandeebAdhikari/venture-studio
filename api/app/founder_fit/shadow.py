"""Capability-match shadow metadata for executive ranking (FF-CM-5)."""

from __future__ import annotations

from app.founder_fit.capability_match import compute_capability_match_score
from app.founder_fit.profiles import PROVISIONAL_DEFAULT_PROFILE


def build_capability_match_shadow_details(
    dominant_fingerprint: str | None,
) -> dict[str, object]:
    """Build informational CM fields for ranking_details without affecting scores."""
    if dominant_fingerprint is None:
        return {
            "capability_match_shadow": True,
            "capability_match_score": None,
            "dominant_fingerprint": None,
        }

    result = compute_capability_match_score(
        dominant_fingerprint,
        PROVISIONAL_DEFAULT_PROFILE,
    )
    return {
        "capability_match_shadow": True,
        "capability_match_score": result.capability_match_score,
        "capability_match_version": result.capability_match_version,
        "dominant_fingerprint": result.dominant_fingerprint,
        "family_coverage": result.family_coverage,
        "critical_gaps": result.critical_gaps,
    }
