"""Pydantic schemas for categories."""

from uuid import UUID

from pydantic import Field

from app.db.enums import CategoryKind
from app.schemas.common import ORMModel, UUIDSchema


class CategoryBase(ORMModel):
    code: str = Field(max_length=50)
    label: str = Field(max_length=100)
    description: str | None = None
    kind: CategoryKind


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(ORMModel):
    label: str | None = Field(default=None, max_length=100)
    description: str | None = None


class CategoryRead(CategoryBase, UUIDSchema):
    pass


class CategorySummary(ORMModel):
    id: UUID
    code: str
    label: str
    kind: CategoryKind
