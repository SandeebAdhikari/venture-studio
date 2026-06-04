"""Internal pipeline orchestration schemas."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StageOutcome(str, Enum):
    """Semantic result of a stage after evaluating item counters."""

    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageExecutionResult(BaseModel):
    """Normalized metrics returned by each stage executor."""

    items_in: int = 0
    items_out: int = 0
    items_failed: int = 0
    records_processed: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    failed: bool = False
    error: str | None = None


def build_stage_execution_result(
    *,
    items_in: int = 0,
    items_out: int = 0,
    items_failed: int = 0,
    skipped: int = 0,
    records_processed: int = 0,
    metadata: dict[str, Any] | None = None,
    error: str | None = None,
) -> StageExecutionResult:
    """Evaluate item counters and return normalized stage metrics with outcome metadata."""
    meta = dict(metadata or {})
    meta["skipped"] = skipped

    if items_failed > 0 and items_out == 0:
        outcome = StageOutcome.FAILED
        failed = True
        stage_error = error or (
            f"Stage failed: {items_failed} item(s) failed with no successful outputs"
        )
    elif items_in > 0 and items_out == 0 and items_failed == 0 and skipped > 0:
        outcome = StageOutcome.SKIPPED
        failed = False
        stage_error = None
    else:
        outcome = StageOutcome.COMPLETED
        failed = False
        stage_error = error

    meta["outcome"] = outcome.value
    return StageExecutionResult(
        items_in=items_in,
        items_out=items_out,
        items_failed=items_failed,
        records_processed=records_processed,
        metadata=meta,
        failed=failed,
        error=stage_error if failed else None,
    )
