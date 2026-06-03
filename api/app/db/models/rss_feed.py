"""RSS feed configuration linked to collection sources."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.source import Source


class RssFeed(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "rss_feeds"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    feed_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    polling_interval_sec: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="3600"
    )
    entry_limit: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[Source] = relationship()

    __table_args__ = (
        CheckConstraint("polling_interval_sec >= 60", name="ck_rss_feeds_polling_interval"),
        CheckConstraint("entry_limit >= 1", name="ck_rss_feeds_entry_limit"),
        Index("idx_rss_feeds_enabled", "enabled"),
        Index("idx_rss_feeds_category", "category"),
        Index("idx_rss_feeds_last_polled", "last_polled_at"),
    )
