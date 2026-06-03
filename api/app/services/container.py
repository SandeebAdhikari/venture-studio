"""Service container wiring repositories to services."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.classification.service import ComplaintClassificationService
from app.agents.competitor_intelligence.service import CompetitorIntelligenceService
from app.agents.customer_research.service import CustomerResearchService
from app.agents.market_research.service import MarketResearchService
from app.agents.revenue_validation.service import RevenueValidationService
from app.agents.opportunity.service import OpportunityGeneratorService
from app.collection.service import ComplaintCollectionService
from app.repositories import RepositoryContainer, get_repositories
from app.reports.executive.service import ExecutiveReportService
from app.scoring.service import OpportunityScoringService
from app.services.category import CategoryService
from app.services.complaint import ComplaintService
from app.services.opportunity import OpportunityService
from app.services.report import ReportService
from app.services.source import SourceService


class ServiceContainer:
    def __init__(self, repos: RepositoryContainer) -> None:
        self.sources = SourceService(repos)
        self.collection = ComplaintCollectionService(repos)
        self.classification = ComplaintClassificationService(repos)
        self.generation = OpportunityGeneratorService(repos)
        self.categories = CategoryService(repos)
        self.complaints = ComplaintService(repos)
        self.opportunities = OpportunityService(repos)
        self.scoring = OpportunityScoringService(repos)
        self.reports = ReportService(repos)
        self.executive_reports = ExecutiveReportService(repos)
        self.market_research = MarketResearchService(repos)
        self.competitor_intelligence = CompetitorIntelligenceService(repos)
        self.customer_research = CustomerResearchService(repos)
        self.revenue_validation = RevenueValidationService(repos)


def get_services(session: AsyncSession) -> ServiceContainer:
    return ServiceContainer(get_repositories(session))
