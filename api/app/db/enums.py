"""Shared database enumerations."""

import enum


class SourceType(str, enum.Enum):
    REDDIT = "reddit"
    HN_ALGOLIA = "hn_algolia"
    RSS = "rss"


class RssFeedCategory(str, enum.Enum):
    BUSINESS = "business"
    INDUSTRY = "industry"
    STARTUP = "startup"
    TECH = "tech"
    HEALTHCARE = "healthcare"
    CONSTRUCTION = "construction"
    LEGAL = "legal"
    GENERAL = "general"


class SignalProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    CLASSIFIED = "classified"
    SKIPPED = "skipped"
    FAILED = "failed"


class CategoryKind(str, enum.Enum):
    COMPLAINT_CATEGORY = "complaint_category"
    DOMAIN = "domain"
    PERSONA = "persona"


class ReviewStatus(str, enum.Enum):
    NEW = "new"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ReportType(str, enum.Enum):
    OPPORTUNITY_BRIEF = "opportunity_brief"
    TOP_OPPORTUNITIES = "top_opportunities"
    VENTURE_RECOMMENDATION = "venture_recommendation"
    DAILY_DIGEST = "daily_digest"
    PIPELINE_SUMMARY = "pipeline_summary"
    CUSTOM = "custom"


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class MarketResearchStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CompetitorAnalysisStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReviewSentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class CustomerResearchStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CustomerEvidenceType(str, enum.Enum):
    COMPLAINT = "complaint"
    DISCUSSION = "discussion"
    REVIEW = "review"
    FORUM = "forum"
    SOCIAL = "social"


class RevenueValidationStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProductStrategyStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class GTMPlanStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class GrowthEvaluationStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class HumanProxyEvaluationStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class FounderRecommendation(str, enum.Enum):
    PURSUE = "pursue"
    EXPLORE = "explore"
    DEFER = "defer"
    PASS = "pass"


class ExecutiveRankingStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStage(str, enum.Enum):
    """Ordered stages in the full Venture Studio pipeline."""

    COLLECT = "collect"
    CLASSIFY = "classify"
    GENERATE_OPPORTUNITIES = "generate_opportunities"
    SCORE_OPPORTUNITIES = "score_opportunities"
    MARKET_RESEARCH = "market_research"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    CUSTOMER_RESEARCH = "customer_research"
    REVENUE_VALIDATION = "revenue_validation"
    PRODUCT_STRATEGY = "product_strategy"
    GO_TO_MARKET = "go_to_market"
    GROWTH_STRATEGY = "growth_strategy"
    HUMAN_PROXY = "human_proxy"
    EXECUTIVE_RANKING = "executive_ranking"
    VENTURE_REPORT = "venture_report"


class PipelineRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStageStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class PipelineTrigger(str, enum.Enum):
    API = "api"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
