"""Executive ranking runs aggregating all agent outputs."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import ExecutiveRankingStatus

if TYPE_CHECKING:
    from app.db.models.executive_ranking_entry import ExecutiveRankingEntry
    from app.db.models.founder_profile import FounderProfile


class ExecutiveRankingRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "executive_ranking_runs"

    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    status: Mapped[ExecutiveRankingStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=ExecutiveRankingStatus.COMPLETED.value,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    founder_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("founder_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    top_n: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    opportunity_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    ranked_opportunity_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    ranking_engine: Mapped[str] = mapped_column(String(50), nullable=False)
    ranking_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    founder_profile: Mapped[FounderProfile | None] = relationship()
    entries: Mapped[list[ExecutiveRankingEntry]] = relationship(
        back_populates="ranking_run",
        cascade="all, delete-orphan",
        order_by="ExecutiveRankingEntry.rank",
    )

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_executive_ranking_runs_version"),
        CheckConstraint("top_n >= 1", name="ck_executive_ranking_runs_top_n"),
        Index(
            "idx_executive_ranking_runs_current",
            "is_current",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
        Index("idx_executive_ranking_runs_version", "version"),
        Index("idx_executive_ranking_runs_status", "status"),
    )
