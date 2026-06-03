"""Pydantic schema utilities."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base schema with ORM attribute loading enabled."""

    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(ORMModel):
    created_at: datetime
    updated_at: datetime


class UUIDSchema(TimestampSchema):
    id: UUID
