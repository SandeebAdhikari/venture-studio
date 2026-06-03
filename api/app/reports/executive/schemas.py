"""Schemas for executive reports."""

from uuid import UUID

from pydantic import BaseModel, Field


class KeyComplaintEntry(BaseModel):
    id: UUID
    summary: str
    verbatim_quote: str
    severity: int = Field(ge=1, le=5)
    source_url: str | None = None


class TopOpportunityEntry(BaseModel):
    opportunity_id: UUID
    title: str
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    recommendation: str
    supporting_evidence_count: int
    supporting_evidence: list[KeyComplaintEntry]
    key_complaints: list[KeyComplaintEntry]
    problem_statement: str
    frequency_signal: str
    gap: str


class ExecutiveReportContent(BaseModel):
    format: str = "markdown"
    markdown: str
    opportunities: list[TopOpportunityEntry] = Field(default_factory=list)
    generated_count: int = 0


class ExecutiveReportResult(BaseModel):
    report_id: UUID
    title: str
    summary: str
    markdown: str
    content: ExecutiveReportContent


class ReportMarkdownRead(BaseModel):
    report_id: UUID
    title: str
    report_type: str
    markdown: str
