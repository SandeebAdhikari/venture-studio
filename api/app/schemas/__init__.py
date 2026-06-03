"""Pydantic schemas package."""

from app.schemas.category import (
    CategoryCreate,
    CategoryRead,
    CategorySummary,
    CategoryUpdate,
)
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintDetail,
    ComplaintRead,
    ComplaintUpdate,
)
from app.schemas.opportunity import (
    OpportunityCreate,
    OpportunityDetail,
    OpportunityRead,
    OpportunityUpdate,
)
from app.schemas.opportunity_score import (
    OpportunityScoreCreate,
    OpportunityScoreRead,
    OpportunityScoreUpdate,
)
from app.schemas.report import ReportCreate, ReportRead, ReportUpdate
from app.schemas.source import SourceCreate, SourceRead, SourceSummary, SourceUpdate

__all__ = [
    "CategoryCreate",
    "CategoryRead",
    "CategorySummary",
    "CategoryUpdate",
    "ComplaintCreate",
    "ComplaintDetail",
    "ComplaintRead",
    "ComplaintUpdate",
    "OpportunityCreate",
    "OpportunityDetail",
    "OpportunityRead",
    "OpportunityUpdate",
    "OpportunityScoreCreate",
    "OpportunityScoreRead",
    "OpportunityScoreUpdate",
    "ReportCreate",
    "ReportRead",
    "ReportUpdate",
    "SourceCreate",
    "SourceRead",
    "SourceSummary",
    "SourceUpdate",
]
