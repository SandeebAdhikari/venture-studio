"""Repository layer — data access for persistence entities."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.category import CategoryRepository
from app.repositories.complaint import ComplaintRepository
from app.repositories.competitor_analysis import CompetitorAnalysisRepository
from app.repositories.customer_research import CustomerResearchRepository
from app.repositories.executive_ranking import ExecutiveRankingRepository
from app.repositories.founder_profile import FounderProfileRepository
from app.repositories.growth_evaluation import GrowthEvaluationRepository
from app.repositories.human_proxy_evaluation import HumanProxyEvaluationRepository
from app.repositories.gtm_plan import GTMPlanRepository
from app.repositories.llm_call import LLMCallRepository
from app.repositories.market_brief import MarketBriefRepository
from app.repositories.pipeline import PipelineRepository
from app.repositories.opportunity import OpportunityRepository
from app.repositories.opportunity_score import OpportunityScoreRepository
from app.repositories.product_strategy import ProductStrategyRepository
from app.repositories.report import ReportRepository
from app.repositories.revenue_validation import RevenueValidationRepository
from app.repositories.rss_feed import RssFeedRepository
from app.repositories.scheduler_job import SchedulerJobRepository
from app.repositories.scheduler_run import SchedulerRunRepository
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
        self.founder_profiles = FounderProfileRepository(session)
        self.growth_evaluations = GrowthEvaluationRepository(session)
        self.human_proxy_evaluations = HumanProxyEvaluationRepository(session)
        self.customer_research = CustomerResearchRepository(session)
        self.executive_rankings = ExecutiveRankingRepository(session)
        self.gtm_plans = GTMPlanRepository(session)
        self.llm_calls = LLMCallRepository(session)
        self.market_briefs = MarketBriefRepository(session)
        self.opportunities = OpportunityRepository(session)
        self.pipelines = PipelineRepository(session)
        self.opportunity_scores = OpportunityScoreRepository(session)
        self.product_strategies = ProductStrategyRepository(session)
        self.reports = ReportRepository(session)
        self.revenue_validations = RevenueValidationRepository(session)
        self.rss_feeds = RssFeedRepository(session)
        self.scheduler_jobs = SchedulerJobRepository(session)
        self.scheduler_runs = SchedulerRunRepository(session)


def get_repositories(session: AsyncSession) -> RepositoryContainer:
    return RepositoryContainer(session)


__all__ = [
    "CategoryRepository",
    "ComplaintRepository",
    "CompetitorAnalysisRepository",
    "FounderProfileRepository",
    "GrowthEvaluationRepository",
    "HumanProxyEvaluationRepository",
    "CustomerResearchRepository",
    "ExecutiveRankingRepository",
    "GTMPlanRepository",
    "LLMCallRepository",
    "MarketBriefRepository",
    "PipelineRepository",
    "OpportunityRepository",
    "OpportunityScoreRepository",
    "ProductStrategyRepository",
    "ReportRepository",
    "RevenueValidationRepository",
    "RssFeedRepository",
    "SchedulerJobRepository",
    "SchedulerRunRepository",
    "RepositoryContainer",
    "SignalRepository",
    "SourceRepository",
    "get_repositories",
]
