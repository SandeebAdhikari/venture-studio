"""Unit tests for pipeline stage metric evaluation."""

import pytest

from app.pipeline.schemas import StageOutcome, build_stage_execution_result


@pytest.mark.parametrize(
    ("items_in", "items_out", "items_failed", "skipped", "expected_outcome", "expected_failed"),
    [
        (1, 0, 1, 0, StageOutcome.FAILED, True),
        (2, 0, 2, 0, StageOutcome.FAILED, True),
        (1, 0, 0, 1, StageOutcome.SKIPPED, False),
        (0, 0, 0, 0, StageOutcome.COMPLETED, False),
        (1, 1, 0, 0, StageOutcome.COMPLETED, False),
        (1, 1, 1, 0, StageOutcome.COMPLETED, False),
        (0, 0, 1, 0, StageOutcome.FAILED, True),
    ],
)
def test_build_stage_execution_result_outcomes(
    items_in: int,
    items_out: int,
    items_failed: int,
    skipped: int,
    expected_outcome: StageOutcome,
    expected_failed: bool,
) -> None:
    result = build_stage_execution_result(
        items_in=items_in,
        items_out=items_out,
        items_failed=items_failed,
        skipped=skipped,
    )
    assert result.metadata["outcome"] == expected_outcome.value
    assert result.failed is expected_failed
    if expected_failed:
        assert result.error is not None
    else:
        assert result.error is None


def test_build_stage_execution_result_preserves_custom_error() -> None:
    result = build_stage_execution_result(
        items_in=1,
        items_out=0,
        items_failed=1,
        error="simulated LLM failure",
    )
    assert result.failed is True
    assert result.error == "simulated LLM failure"
    assert result.metadata["outcome"] == StageOutcome.FAILED.value
