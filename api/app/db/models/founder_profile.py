"""Founder profiles for human proxy evaluation."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.human_proxy_evaluation import HumanProxyEvaluation


class FounderProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "founder_profiles"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    constraints: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    profile_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    evaluations: Mapped[list[HumanProxyEvaluation]] = relationship(
        back_populates="founder_profile",
        cascade="all, delete-orphan",
        order_by="desc(HumanProxyEvaluation.created_at)",
    )

    __table_args__ = (
        Index(
            "idx_founder_profiles_default",
            "is_default",
            unique=True,
            postgresql_where=text("is_default = true"),
        ),
        Index("idx_founder_profiles_active", "is_active"),
    )
