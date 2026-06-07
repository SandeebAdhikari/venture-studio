"""Load and cache mechanism requirement matrix artifacts."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.founder_fit.matrix_validator import MatrixValidationError, validate_mechanism_requirement_matrix
from app.founder_fit.schemas import MechanismRequirementMatrix

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_MATRIX_VERSION = "cm_v1"


class MatrixLoadError(RuntimeError):
    """Raised when a matrix artifact cannot be loaded."""


def matrix_artifact_path(matrix_version: str = DEFAULT_MATRIX_VERSION) -> Path:
    return DATA_DIR / f"mechanism_requirement_matrix_{matrix_version}.yaml"


def load_mechanism_requirement_matrix(
    *,
    matrix_version: str = DEFAULT_MATRIX_VERSION,
    path: Path | None = None,
) -> MechanismRequirementMatrix:
    """Load and validate a matrix artifact from disk."""
    artifact_path = path or matrix_artifact_path(matrix_version)
    if not artifact_path.is_file():
        raise MatrixLoadError(f"matrix artifact not found: {artifact_path}")

    try:
        raw: Any = yaml.safe_load(artifact_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise MatrixLoadError(f"failed to parse matrix artifact {artifact_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise MatrixLoadError(f"matrix artifact must be a mapping: {artifact_path}")

    try:
        matrix = MechanismRequirementMatrix.model_validate(raw)
    except Exception as exc:
        raise MatrixLoadError(f"matrix artifact schema invalid: {exc}") from exc

    validate_mechanism_requirement_matrix(matrix)
    return matrix


@lru_cache(maxsize=4)
def get_mechanism_requirement_matrix(
    matrix_version: str = DEFAULT_MATRIX_VERSION,
) -> MechanismRequirementMatrix:
    """Return a cached, validated matrix (loads on first access)."""
    return load_mechanism_requirement_matrix(matrix_version=matrix_version)


def init_mechanism_requirement_matrix(
    *,
    matrix_version: str = DEFAULT_MATRIX_VERSION,
) -> MechanismRequirementMatrix:
    """Load matrix at startup; raises on validation failure."""
    get_mechanism_requirement_matrix.cache_clear()
    matrix = load_mechanism_requirement_matrix(matrix_version=matrix_version)
    get_mechanism_requirement_matrix(matrix_version=matrix_version)
    return matrix


def clear_mechanism_requirement_matrix_cache() -> None:
    get_mechanism_requirement_matrix.cache_clear()


__all__ = [
    "MatrixLoadError",
    "clear_mechanism_requirement_matrix_cache",
    "get_mechanism_requirement_matrix",
    "init_mechanism_requirement_matrix",
    "load_mechanism_requirement_matrix",
    "matrix_artifact_path",
]
