"""Internal pipeline orchestration schemas."""

from typing import Any

from pydantic import BaseModel, Field


class StageExecutionResult(BaseModel):
    """Normalized metrics returned by each stage executor."""

    items_in: int = 0
    items_out: int = 0
    items_failed: int = 0
    records_processed: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    failed: bool = False
    error: str | None = None
