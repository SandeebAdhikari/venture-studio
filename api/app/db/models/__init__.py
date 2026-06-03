"""ORM model registry for Alembic autogenerate."""

from app.db.base import Base
from app.db.models.associations import opportunity_complaints
from app.db.models.category import Category
from app.db.models.competitor_analysis import CompetitorAnalysis
from app.db.models.competitor_profile import CompetitorProfile
from app.db.models.customer_research import CustomerResearch
from app.db.models.customer_research_evidence import CustomerResearchEvidence
from app.db.models.complaint import Complaint
from app.db.models.llm_call import LLMCall
from app.db.models.market_brief import MarketBrief
from app.db.models.opportunity import Opportunity
from app.db.models.opportunity_score import OpportunityScore
from app.db.models.report import Report
from app.db.models.growth_evaluation import GrowthEvaluation
from app.db.models.growth_evaluation_evidence import GrowthEvaluationEvidence
from app.db.models.gtm_plan import GTMPlan
from app.db.models.gtm_plan_evidence import GTMPlanEvidence
from app.db.models.product_strategy import ProductStrategy
from app.db.models.product_strategy_evidence import ProductStrategyEvidence
from app.db.models.revenue_validation import RevenueValidation
from app.db.models.revenue_validation_evidence import RevenueValidationEvidence
from app.db.models.signal import Signal
from app.db.models.source import Source

__all__ = [
    "Base",
    "Category",
    "CompetitorAnalysis",
    "CompetitorProfile",
    "CustomerResearch",
    "CustomerResearchEvidence",
    "Complaint",
    "GrowthEvaluation",
    "GrowthEvaluationEvidence",
    "GTMPlan",
    "GTMPlanEvidence",
    "LLMCall",
    "MarketBrief",
    "Opportunity",
    "OpportunityScore",
    "ProductStrategy",
    "ProductStrategyEvidence",
    "Report",
    "RevenueValidation",
    "RevenueValidationEvidence",
    "Signal",
    "Source",
    "opportunity_complaints",
]
