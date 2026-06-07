"""Validation for mechanism requirement matrix artifacts."""

from __future__ import annotations

import math
from collections import Counter

from app.agents.opportunity.mechanism_fingerprints import MECHANISM_FINGERPRINTS
from app.founder_fit.capability_families import CAPABILITY_FAMILIES
from app.founder_fit.schemas import MechanismRequirementMatrix, MechanismRequirementSpec

WEIGHT_SUM_TOLERANCE = 1e-6


class MatrixValidationError(ValueError):
    """Raised when a mechanism requirement matrix fails validation."""


def validate_mechanism_requirement_matrix(matrix: MechanismRequirementMatrix) -> None:
    """Validate matrix structure and content. Raises MatrixValidationError on failure."""
    if not matrix.matrix_version:
        raise MatrixValidationError("matrix_version is required")

    if not matrix.specs:
        raise MatrixValidationError("matrix must contain at least one requirement spec")

    seen_fingerprints: set[str] = set()

    for spec in matrix.specs:
        _validate_spec(spec, root_version=matrix.matrix_version, seen_fingerprints=seen_fingerprints)

    missing = MECHANISM_FINGERPRINTS - seen_fingerprints
    if missing:
        raise MatrixValidationError(
            "matrix is missing requirement specs for fingerprints: "
            + ", ".join(sorted(missing))
        )

    extra = seen_fingerprints - MECHANISM_FINGERPRINTS
    if extra:
        raise MatrixValidationError(
            "matrix contains unknown fingerprints: " + ", ".join(sorted(extra))
        )


def _validate_spec(
    spec: MechanismRequirementSpec,
    *,
    root_version: str,
    seen_fingerprints: set[str],
) -> None:
    if spec.fingerprint not in MECHANISM_FINGERPRINTS:
        raise MatrixValidationError(f"unknown fingerprint: {spec.fingerprint}")

    if spec.fingerprint in seen_fingerprints:
        raise MatrixValidationError(f"duplicate fingerprint: {spec.fingerprint}")
    seen_fingerprints.add(spec.fingerprint)

    if not spec.matrix_version:
        raise MatrixValidationError(f"{spec.fingerprint}: matrix_version is required")

    if spec.matrix_version != root_version:
        raise MatrixValidationError(
            f"{spec.fingerprint}: matrix_version {spec.matrix_version!r} "
            f"does not match root {root_version!r}"
        )

    if not spec.requirements:
        raise MatrixValidationError(f"{spec.fingerprint}: at least one requirement is required")

    role_counts = Counter(requirement.role for requirement in spec.requirements)
    if role_counts.get("primary", 0) != 1:
        raise MatrixValidationError(
            f"{spec.fingerprint}: expected exactly one primary requirement, "
            f"found {role_counts.get('primary', 0)}"
        )

    weight_total = sum(requirement.weight for requirement in spec.requirements)
    if not math.isclose(weight_total, 1.0, abs_tol=WEIGHT_SUM_TOLERANCE):
        raise MatrixValidationError(
            f"{spec.fingerprint}: requirement weights must sum to 1.0, got {weight_total}"
        )

    declared_families = set(spec.families)
    requirement_families = {requirement.family for requirement in spec.requirements}
    if declared_families != requirement_families:
        raise MatrixValidationError(
            f"{spec.fingerprint}: families list must match requirement families"
        )

    for requirement in spec.requirements:
        if requirement.family not in CAPABILITY_FAMILIES:
            raise MatrixValidationError(
                f"{spec.fingerprint}: unknown capability family {requirement.family!r}"
            )
        if not 0 <= requirement.min_viable <= 100:
            raise MatrixValidationError(
                f"{spec.fingerprint}: min_viable must be in [0, 100], "
                f"got {requirement.min_viable}"
            )

    confidence = spec.metadata.confidence
    if confidence not in {"high", "medium", "low"}:
        raise MatrixValidationError(
            f"{spec.fingerprint}: invalid confidence value {confidence!r}"
        )
