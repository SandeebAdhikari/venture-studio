"""Tests for mechanism requirement matrix loader and validator."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agents.opportunity.mechanism_fingerprints import MECHANISM_FINGERPRINTS
from app.founder_fit.matrix_loader import (
    clear_mechanism_requirement_matrix_cache,
    load_mechanism_requirement_matrix,
    matrix_artifact_path,
)
from app.founder_fit.matrix_validator import MatrixValidationError, validate_mechanism_requirement_matrix
from app.founder_fit.schemas import MechanismRequirementMatrix


@pytest.fixture(autouse=True)
def _clear_matrix_cache() -> None:
    clear_mechanism_requirement_matrix_cache()


def test_matrix_loads_successfully() -> None:
    matrix = load_mechanism_requirement_matrix()
    assert matrix.matrix_version == "cm_v1"
    assert len(matrix.specs) == 34


def test_all_34_fingerprints_present() -> None:
    matrix = load_mechanism_requirement_matrix()
    loaded = {spec.fingerprint for spec in matrix.specs}
    assert loaded == set(MECHANISM_FINGERPRINTS)


def test_weight_sums_validated() -> None:
    matrix = load_mechanism_requirement_matrix()
    for spec in matrix.specs:
        total = sum(requirement.weight for requirement in spec.requirements)
        assert abs(total - 1.0) < 1e-6


def test_invalid_family_rejected(tmp_path: Path) -> None:
    matrix = load_mechanism_requirement_matrix()
    payload = matrix.model_dump(mode="json")
    payload["specs"][0]["requirements"][0]["family"] = "not_a_real_family"
    payload["specs"][0]["families"] = [
        req["family"] for req in payload["specs"][0]["requirements"]
    ]
    invalid = MechanismRequirementMatrix.model_validate(payload)
    with pytest.raises(MatrixValidationError, match="unknown capability family"):
        validate_mechanism_requirement_matrix(invalid)


def test_invalid_fingerprint_rejected(tmp_path: Path) -> None:
    matrix = load_mechanism_requirement_matrix()
    payload = matrix.model_dump(mode="json")
    payload["specs"][0]["fingerprint"] = "not_a_real_fingerprint"
    invalid = MechanismRequirementMatrix.model_validate(payload)
    with pytest.raises(MatrixValidationError, match="unknown fingerprint"):
        validate_mechanism_requirement_matrix(invalid)


def test_missing_primary_rejected() -> None:
    matrix = load_mechanism_requirement_matrix()
    payload = matrix.model_dump(mode="json")
    spec = payload["specs"][0]
    spec["requirements"][0]["role"] = "secondary"
    spec["requirements"][1]["role"] = "optional"
    invalid = MechanismRequirementMatrix.model_validate(payload)
    with pytest.raises(MatrixValidationError, match="exactly one primary"):
        validate_mechanism_requirement_matrix(invalid)


def test_invalid_confidence_rejected() -> None:
    matrix = load_mechanism_requirement_matrix()
    payload = matrix.model_dump(mode="json")
    payload["specs"][0]["metadata"]["confidence"] = "very_high"
    with pytest.raises(Exception):
        MechanismRequirementMatrix.model_validate(payload)


def test_matrix_artifact_path_points_to_cm_v1_file() -> None:
    path = matrix_artifact_path("cm_v1")
    assert path.name == "mechanism_requirement_matrix_cm_v1.yaml"
    assert path.is_file()


def test_invalid_weight_sum_rejected(tmp_path: Path) -> None:
    matrix = load_mechanism_requirement_matrix()
    payload = matrix.model_dump(mode="json")
    payload["specs"][0]["requirements"][0]["weight"] = 0.99
    invalid = MechanismRequirementMatrix.model_validate(payload)
    with pytest.raises(MatrixValidationError, match="weights must sum to 1.0"):
        validate_mechanism_requirement_matrix(invalid)


def test_missing_fingerprint_rejected() -> None:
    matrix = load_mechanism_requirement_matrix()
    payload = matrix.model_dump(mode="json")
    payload["specs"] = payload["specs"][:-1]
    incomplete = MechanismRequirementMatrix.model_validate(payload)
    with pytest.raises(MatrixValidationError, match="missing requirement specs"):
        validate_mechanism_requirement_matrix(incomplete)


def test_example_matrix_entry_structure() -> None:
    matrix = load_mechanism_requirement_matrix()
    example = next(
        spec for spec in matrix.specs if spec.fingerprint == "ai_eval_pipeline_gap"
    )
    assert example.matrix_version == "cm_v1"
    assert example.metadata.confidence == "high"
    assert example.audit.approved_by == "ff_cm_3"
    primary = [req for req in example.requirements if req.role == "primary"]
    assert len(primary) == 1
    assert primary[0].family == "ai_ml_operations"
    assert primary[0].critical is True
