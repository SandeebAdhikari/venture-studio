"""Association table linking opportunities to evidence complaints."""

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

opportunity_complaints = Table(
    "opportunity_complaints",
    Base.metadata,
    Column(
        "opportunity_id",
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "complaint_id",
        UUID(as_uuid=True),
        ForeignKey("complaints.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
