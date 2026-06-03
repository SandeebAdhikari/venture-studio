"""ORM model registry for Alembic autogenerate."""

from app.db.base import Base
from app.db.models.associations import opportunity_complaints
from app.db.models.category import Category
from app.db.models.complaint import Complaint
from app.db.models.llm_call import LLMCall
from app.db.models.opportunity import Opportunity
from app.db.models.opportunity_score import OpportunityScore
from app.db.models.report import Report
from app.db.models.signal import Signal
from app.db.models.source import Source

__all__ = [
    "Base",
    "Category",
    "Complaint",
    "LLMCall",
    "Opportunity",
    "OpportunityScore",
    "Report",
    "Signal",
    "Source",
    "opportunity_complaints",
]
