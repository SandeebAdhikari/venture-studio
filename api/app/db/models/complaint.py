"""Structured complaint extracted from a signal."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.category import Category
    from app.db.models.opportunity import Opportunity
    from app.db.models.signal import Signal


class Complaint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "complaints"

    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    verbatim_quote: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    product_mentions: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default="{}",
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    signal: Mapped[Signal] = relationship(back_populates="complaint")
    category: Mapped[Category] = relationship(
        back_populates="complaints_as_category",
        foreign_keys=[category_id],
    )
    domain: Mapped[Category] = relationship(
        back_populates="complaints_as_domain",
        foreign_keys=[domain_id],
    )
    persona: Mapped[Category] = relationship(
        back_populates="complaints_as_persona",
        foreign_keys=[persona_id],
    )
    opportunities: Mapped[list[Opportunity]] = relationship(
        secondary="opportunity_complaints",
        back_populates="complaints",
    )

    __table_args__ = (
        CheckConstraint("severity >= 1 AND severity <= 5", name="ck_complaints_severity"),
        Index("idx_complaints_category_domain", "category_id", "domain_id"),
        Index("idx_complaints_severity", "severity"),
    )
