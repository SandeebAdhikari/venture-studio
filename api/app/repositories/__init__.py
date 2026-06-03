"""Repository layer — data access for persistence entities."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.category import CategoryRepository
from app.repositories.complaint import ComplaintRepository
from app.repositories.competitor_analysis import CompetitorAnalysisRepository
from app.repositories.llm_call import LLMCallRepository
from app.repositories.market_brief import MarketBriefRepository
from app.repositories.opportunity import OpportunityRepository
from app.repositories.opportunity_score import OpportunityScoreRepository
from app.repositories.report import ReportRepository
from app.repositories.signal import SignalRepository
from app.repositories.source import SourceRepository


class RepositoryContainer:
    """Groups repositories sharing a single database session."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sources = SourceRepository(session)
        self.signals = SignalRepository(session)
        self.categories = CategoryRepository(session)
        self.complaints = ComplaintRepository(session)
        self.competitor_analyses = CompetitorAnalysisRepository(session)
        self.llm_calls = LLMCallRepository(session)
        self.market_briefs = MarketBriefRepository(session)
        self.opportunities = OpportunityRepository(session)
        self.opportunity_scores = OpportunityScoreRepository(session)
        self.reports = ReportRepository(session)


def get_repositories(session: AsyncSession) -> RepositoryContainer:
    return RepositoryContainer(session)


__all__ = [
    "CategoryRepository",
    "ComplaintRepository",
    "CompetitorAnalysisRepository",
    "LLMCallRepository",
    "MarketBriefRepository",
    "OpportunityRepository",
    "OpportunityScoreRepository",
    "ReportRepository",
    "RepositoryContainer",
    "SignalRepository",
    "SourceRepository",
    "get_repositories",
]
