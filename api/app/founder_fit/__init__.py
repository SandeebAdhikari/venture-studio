"""Founder-fit capability matrix and deterministic scoring (FF-CM)."""

from app.founder_fit.capability_match import (
    CAPABILITY_MATCH_VERSION,
    compute_capability_match_score,
    coverage,
)
from app.founder_fit.errors import (
    CapabilityMatchError,
    InvalidCapabilityLevelError,
    MissingCapabilityScoreError,
    UnknownCapabilityFamilyError,
    UnknownFingerprintError,
)
from app.founder_fit.matrix_loader import (
    MatrixLoadError,
    get_mechanism_requirement_matrix,
    init_mechanism_requirement_matrix,
    load_mechanism_requirement_matrix,
)
from app.founder_fit.matrix_validator import MatrixValidationError
from app.founder_fit.profiles import (
    FULL_COVERAGE_PROFILE,
    PROVISIONAL_DEFAULT_PROFILE,
    FounderCapabilitiesProfile,
)
from app.founder_fit.schemas import (
    CapabilityMatchResult,
    MechanismRequirementMatrix,
    MechanismRequirementSpec,
)

__all__ = [
    "CAPABILITY_MATCH_VERSION",
    "CapabilityMatchError",
    "CapabilityMatchResult",
    "FULL_COVERAGE_PROFILE",
    "FounderCapabilitiesProfile",
    "InvalidCapabilityLevelError",
    "MatrixLoadError",
    "MatrixValidationError",
    "MechanismRequirementMatrix",
    "MechanismRequirementSpec",
    "MissingCapabilityScoreError",
    "PROVISIONAL_DEFAULT_PROFILE",
    "UnknownCapabilityFamilyError",
    "UnknownFingerprintError",
    "compute_capability_match_score",
    "coverage",
    "get_mechanism_requirement_matrix",
    "init_mechanism_requirement_matrix",
    "load_mechanism_requirement_matrix",
]
