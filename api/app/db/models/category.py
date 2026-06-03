"""Taxonomy categories for complaint classification."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import CategoryKind

if TYPE_CHECKING:
    from app.db.models.complaint import Complaint


class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "categories"

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    kind: Mapped[CategoryKind] = mapped_column(String(30), nullable=False)

    complaints_as_category: Mapped[list[Complaint]] = relationship(
        back_populates="category",
        foreign_keys="Complaint.category_id",
    )
    complaints_as_domain: Mapped[list[Complaint]] = relationship(
        back_populates="domain",
        foreign_keys="Complaint.domain_id",
    )
    complaints_as_persona: Mapped[list[Complaint]] = relationship(
        back_populates="persona",
        foreign_keys="Complaint.persona_id",
    )

    __table_args__ = (
        UniqueConstraint("code", "kind", name="uq_categories_code_kind"),
        Index("idx_categories_kind", "kind"),
    )
