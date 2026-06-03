"""Raw ingested content from a source."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.enums import SignalProcessingStatus

if TYPE_CHECKING:
    from app.db.models.complaint import Complaint
    from app.db.models.source import Source


class Signal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Supporting entity: complaints are extracted from signals."""

    __tablename__ = "signals"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signal_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    processing_status: Mapped[SignalProcessingStatus] = mapped_column(
        String(30),
        nullable=False,
        server_default=SignalProcessingStatus.PENDING.value,
    )
    skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    source: Mapped[Source] = relationship(back_populates="signals")
    complaint: Mapped[Complaint | None] = relationship(
        back_populates="signal",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_signals_source_external"),
        Index("idx_signals_status_collected", "processing_status", "collected_at"),
        Index("idx_signals_published", "published_at"),
        Index("idx_signals_source_content_hash", "source_id", "content_hash"),
    )
