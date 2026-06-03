"""Individual founder decisions on approval requests."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.approval_request import ApprovalRequest


class ApprovalDecision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "approval_decisions"

    approval_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision_type: Mapped[str] = mapped_column(String(30), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False, server_default="founder")
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    approval_request: Mapped[ApprovalRequest] = relationship(back_populates="decisions")

    __table_args__ = (
        Index("idx_approval_decisions_request", "approval_request_id"),
        Index("idx_approval_decisions_created", "created_at"),
    )
