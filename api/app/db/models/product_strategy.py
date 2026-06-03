"""Product strategy plans for opportunities."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import ProductStrategyStatus

if TYPE_CHECKING:
    from app.db.models.opportunity import Opportunity
    from app.db.models.product_strategy_evidence import ProductStrategyEvidence


class ProductStrategy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "product_strategies"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[ProductStrategyStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=ProductStrategyStatus.COMPLETED.value,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    mvp_definition: Mapped[str] = mapped_column(Text, nullable=False)
    core_features: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    feature_priorities: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    development_phases: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    estimated_timeline: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    technical_risks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    roadmap: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    planning_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    llm_model: Mapped[str] = mapped_column(String(50), nullable=False)
    strategy_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    opportunity: Mapped[Opportunity] = relationship(back_populates="product_strategies")
    evidence: Mapped[list[ProductStrategyEvidence]] = relationship(
        back_populates="product_strategy",
        cascade="all, delete-orphan",
        order_by="ProductStrategyEvidence.created_at",
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_product_strategies_version"),
        Index("idx_product_strategies_opportunity", "opportunity_id", "created_at"),
        Index(
            "idx_product_strategies_current",
            "opportunity_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        Index("idx_product_strategies_status", "status"),
    )
