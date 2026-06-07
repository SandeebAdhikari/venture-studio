"""Tests for deterministic capability match scoring (FF-CM-3B)."""

from __future__ import annotations

import pytest

from app.founder_fit.capability_match import compute_capability_match_score, coverage
from app.founder_fit.errors import (
    InvalidCapabilityLevelError,
    MissingCapabilityScoreError,
    UnknownCapabilityFamilyError,
    UnknownFingerprintError,
)
from app.founder_fit.matrix_loader import load_mechanism_requirement_matrix
from app.founder_fit.profiles import (
    FULL_COVERAGE_PROFILE,
    PROVISIONAL_DEFAULT_PROFILE,
    FounderCapabilitiesProfile,
)


def test_coverage_piecewise_mid_band() -> None:
    assert coverage(60, 65) == pytest.approx(60 / 65)
    assert coverage(65, 65) == 1.0
    assert coverage(32, 65) == pytest.approx(0.25 * 32 / (65 * 0.5))


def test_full_coverage_founder_scores_100() -> None:
    result = compute_capability_match_score("ai_eval_pipeline_gap", FULL_COVERAGE_PROFILE)
    assert result.capability_match_score == 100
    assert result.critical_gaps == []
    assert result.capability_match_version == "capability_match_v1"
    assert result.dominant_fingerprint == "ai_eval_pipeline_gap"
    assert all(value == 1.0 for value in result.family_coverage.values())


def test_partial_coverage_founder_ai_eval_pipeline() -> None:
    result = compute_capability_match_score("ai_eval_pipeline_gap", PROVISIONAL_DEFAULT_PROFILE)
    assert result.capability_match_score == 96
    assert result.family_coverage["ai_ml_operations"] == pytest.approx(60 / 65)
    assert result.family_coverage["python_data"] == 1.0
    assert result.family_coverage["devops_cicd"] == 1.0
    assert result.critical_gaps == []


def test_critical_gap_founder_caps_at_40() -> None:
    profile: FounderCapabilitiesProfile = dict(PROVISIONAL_DEFAULT_PROFILE)
    profile["security_engineering"] = 20
    result = compute_capability_match_score("session_fixation_exposure", profile)
    assert result.capability_match_score == 40
    assert result.critical_gaps == ["security_engineering"]


def test_security_fingerprint_weak_security_capability() -> None:
    result = compute_capability_match_score("session_fixation_exposure", PROVISIONAL_DEFAULT_PROFILE)
    assert result.capability_match_score == 40
    assert "security_engineering" in result.critical_gaps
    assert result.family_coverage["security_engineering"] == pytest.approx(
        0.25 * 25 / (65 * 0.5)
    )


def test_fintech_fingerprint_weak_payments_capability() -> None:
    result = compute_capability_match_score(
        "processor_account_deplatforming",
        PROVISIONAL_DEFAULT_PROFILE,
    )
    assert result.capability_match_score == 14
    assert "payments_billing" in result.critical_gaps
    assert result.family_coverage["payments_billing"] == pytest.approx(
        0.25 * 20 / (70 * 0.5)
    )


def test_deterministic_repeatability() -> None:
    first = compute_capability_match_score("ai_eval_pipeline_gap", PROVISIONAL_DEFAULT_PROFILE)
    second = compute_capability_match_score("ai_eval_pipeline_gap", PROVISIONAL_DEFAULT_PROFILE)
    assert first == second
    assert first.capability_match_score == 96


def test_matrix_lookup_failure_unknown_fingerprint() -> None:
    with pytest.raises(UnknownFingerprintError, match="not_a_real_fingerprint"):
        compute_capability_match_score("not_a_real_fingerprint", PROVISIONAL_DEFAULT_PROFILE)


def test_capability_validation_unknown_family() -> None:
    profile = dict(PROVISIONAL_DEFAULT_PROFILE)
    profile["unknown_family"] = 50  # type: ignore[literal-required]
    with pytest.raises(UnknownCapabilityFamilyError, match="unknown_family"):
        compute_capability_match_score("ai_eval_pipeline_gap", profile)


def test_capability_validation_missing_family_score() -> None:
    profile = {
        "ai_ml_operations": 60,
        "python_data": 75,
    }
    with pytest.raises(MissingCapabilityScoreError, match="devops_cicd"):
        compute_capability_match_score("ai_eval_pipeline_gap", profile)


def test_capability_validation_invalid_level() -> None:
    profile = dict(PROVISIONAL_DEFAULT_PROFILE)
    profile["ai_ml_operations"] = 150
    with pytest.raises(InvalidCapabilityLevelError, match="ai_ml_operations"):
        compute_capability_match_score("ai_eval_pipeline_gap", profile)


def test_custom_matrix_isolation() -> None:
    matrix = load_mechanism_requirement_matrix()
    result = compute_capability_match_score(
        "gpu_compute_access_unreliability",
        PROVISIONAL_DEFAULT_PROFILE,
        matrix=matrix,
    )
    assert result.capability_match_score == 92
    assert result.dominant_fingerprint == "gpu_compute_access_unreliability"
