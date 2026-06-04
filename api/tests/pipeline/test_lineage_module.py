"""Unit tests for pipeline lineage metadata helpers."""

from uuid import uuid4

from app.pipeline.lineage import (
    PIPELINE_RUN_ID_METADATA_KEY,
    merge_pipeline_run_lineage,
    pipeline_run_id_from_metadata,
)


def test_pipeline_run_id_key_constant() -> None:
    assert PIPELINE_RUN_ID_METADATA_KEY == "pipeline_run_id"


def test_merge_does_not_mutate_input() -> None:
    original = {"a": 1}
    run_id = uuid4()
    merged = merge_pipeline_run_lineage(original, pipeline_run_id=run_id)
    assert original == {"a": 1}
    assert merged[PIPELINE_RUN_ID_METADATA_KEY] == str(run_id)
