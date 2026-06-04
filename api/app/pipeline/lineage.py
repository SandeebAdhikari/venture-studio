"""Metadata-only pipeline lineage (no FK migrations)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

PIPELINE_RUN_ID_METADATA_KEY = "pipeline_run_id"


def merge_pipeline_run_lineage(
    metadata: dict[str, Any],
    *,
    pipeline_run_id: UUID | None,
) -> dict[str, Any]:
    """Return a copy of metadata with pipeline_run_id set when provided."""
    result = dict(metadata)
    if pipeline_run_id is not None:
        result[PIPELINE_RUN_ID_METADATA_KEY] = str(pipeline_run_id)
    return result


def pipeline_run_id_from_metadata(metadata: dict[str, Any] | None) -> UUID | None:
    """Parse pipeline_run_id from ranking_metadata or report_metadata."""
    if not metadata:
        return None
    raw = metadata.get(PIPELINE_RUN_ID_METADATA_KEY)
    if raw is None:
        return None
    return UUID(str(raw))
