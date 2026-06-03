"""Pydantic schemas for sources."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.db.enums import SourceType
from app.schemas.common import ORMModel, TimestampSchema, UUIDSchema


class SourceBase(ORMModel):
    name: str = Field(max_length=100)
    source_type: SourceType
    config: dict[str, Any]
    enabled: bool = True


class SourceCreate(SourceBase):
    pass


class SourceUpdate(ORMModel):
    name: str | None = Field(default=None, max_length=100)
    source_type: SourceType | None = None
    config: dict[str, Any] | None = None
    enabled: bool | None = None
    last_collected_at: datetime | None = None
    last_error: str | None = None


class SourceRead(SourceBase, UUIDSchema):
    last_collected_at: datetime | None = None
    last_error: str | None = None


class SourceSummary(TimestampSchema):
    id: UUID
    name: str
    source_type: SourceType
    enabled: bool
