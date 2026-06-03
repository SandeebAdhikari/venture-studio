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
    DAILY_DIGEST = "daily_digest"
    PIPELINE_SUMMARY = "pipeline_summary"
    CUSTOM = "custom"


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
