"""Schemas for the complaint collection pipeline."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RawComplaintInput(BaseModel):
    """Raw complaint/signal payload from an external source or adapter."""

    external_id: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1)
    body: str = Field(min_length=1)
    title: str | None = None
    author: str | None = Field(default=None, max_length=255)
    published_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RawComplaintBatch(BaseModel):
    source_id: UUID
    items: list[RawComplaintInput] = Field(min_length=1)


CollectionItemStatus = Literal["inserted", "duplicate", "skipped"]


class CollectionItemResult(BaseModel):
    external_id: str
    status: CollectionItemStatus
    signal_id: UUID | None = None
    reason: str | None = None


class CollectionResult(BaseModel):
    source_id: UUID
    inserted: int = 0
    duplicates: int = 0
    skipped: int = 0
    items: list[CollectionItemResult] = Field(default_factory=list)

    def add_item(self, item: CollectionItemResult) -> None:
        self.items.append(item)
        if item.status == "inserted":
            self.inserted += 1
        elif item.status == "duplicate":
            self.duplicates += 1
        elif item.status == "skipped":
            self.skipped += 1


class NormalizedComplaint(BaseModel):
    """Output of the text normalization pipeline."""

    title: str | None
    body: str
    combined_text: str
    content_hash: str
    normalizer_version: str
