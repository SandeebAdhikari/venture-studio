"""Founder profile persistence schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.founder_profile import FounderProfile


class FounderProfileCreate(BaseModel):
    name: str = Field(max_length=120)
    description: str | None = None
    skills: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    is_active: bool = True
    profile_metadata: dict[str, Any] = Field(default_factory=dict)


class FounderProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    skills: list[str]
    constraints: dict[str, Any]
    is_default: bool
    is_active: bool
    profile_metadata: dict[str, Any]

    @classmethod
    def from_entity(cls, entity: FounderProfile) -> "FounderProfileRead":
        return cls(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            skills=entity.skills,
            constraints=entity.constraints,
            is_default=entity.is_default,
            is_active=entity.is_active,
            profile_metadata=entity.profile_metadata,
        )
