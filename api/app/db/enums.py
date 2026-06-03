"""Shared database enumerations."""

import enum


class SourceType(str, enum.Enum):
    REDDIT = "reddit"
    HN_ALGOLIA = "hn_algolia"
    RSS = "rss"


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
