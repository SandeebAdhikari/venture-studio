"""Deterministic capability match scoring (FF-CM-3B)."""

from __future__ import annotations

from app.founder_fit.capability_families import CAPABILITY_FAMILIES
from app.founder_fit.errors import (
    InvalidCapabilityLevelError,
    MissingCapabilityScoreError,
    UnknownCapabilityFamilyError,
    UnknownFingerprintError,
)
from app.founder_fit.matrix_loader import get_mechanism_requirement_matrix
from app.founder_fit.profiles import FounderCapabilitiesProfile
from app.founder_fit.schemas import CapabilityMatchResult, MechanismRequirementMatrix, MechanismRequirementSpec

CAPABILITY_MATCH_VERSION = "capability_match_v1"
CRITICAL_GAP_SCORE_CAP = 40


def coverage(founder_level: int, min_viable: int) -> float:
    """Hybrid piecewise coverage from FF-CM-3."""
    if founder_level >= min_viable:
        return 1.0
    if founder_level >= min_viable * 0.5:
        return founder_level / min_viable
    return 0.25 * founder_level / (min_viable * 0.5)


def _validate_capabilities(
    capabilities: FounderCapabilitiesProfile | dict[str, int],
    spec: MechanismRequirementSpec,
) -> None:
    for family, level in capabilities.items():
        if family not in CAPABILITY_FAMILIES:
            raise UnknownCapabilityFamilyError(family)
        if level < 0 or level > 100:
            raise InvalidCapabilityLevelError(family, level)

    for requirement in spec.requirements:
        if requirement.family not in capabilities:
            raise MissingCapabilityScoreError(requirement.family)
        level = capabilities[requirement.family]
        if level < 0 or level > 100:
            raise InvalidCapabilityLevelError(requirement.family, level)


def _lookup_spec(
    fingerprint: str,
    matrix: MechanismRequirementMatrix,
) -> MechanismRequirementSpec:
    for spec in matrix.specs:
        if spec.fingerprint == fingerprint:
            return spec
    raise UnknownFingerprintError(fingerprint)


def compute_capability_match_score(
    fingerprint: str,
    capabilities: FounderCapabilitiesProfile | dict[str, int],
    *,
    matrix: MechanismRequirementMatrix | None = None,
) -> CapabilityMatchResult:
    """Score founder capability coverage for a single mechanism fingerprint."""
    matrix = matrix or get_mechanism_requirement_matrix()
    spec = _lookup_spec(fingerprint, matrix)
    _validate_capabilities(capabilities, spec)

    family_coverage: dict[str, float] = {}
    critical_gaps: list[str] = []
    weighted_total = 0.0

    for requirement in spec.requirements:
        level = capabilities[requirement.family]
        cov = coverage(level, requirement.min_viable)
        family_coverage[requirement.family] = cov
        weighted_total += requirement.weight * cov

        if requirement.critical and level < requirement.min_viable * 0.5:
            critical_gaps.append(requirement.family)

    score = round(100 * weighted_total)
    if critical_gaps:
        score = min(score, CRITICAL_GAP_SCORE_CAP)

    return CapabilityMatchResult(
        capability_match_score=score,
        family_coverage=family_coverage,
        critical_gaps=critical_gaps,
        dominant_fingerprint=fingerprint,
        capability_match_version=CAPABILITY_MATCH_VERSION,
    )
