"""Schemas for mechanism requirement matrix (FF-CM-3)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

RequirementRole = Literal["primary", "secondary", "optional"]
ConfidenceLevel = Literal["high", "medium", "low"]


class CapabilityRequirement(BaseModel):
    family: str
    role: RequirementRole
    weight: float = Field(ge=0.0, le=1.0)
    min_viable: int = Field(ge=0, le=100)
    critical: bool = False


class RequirementMetadata(BaseModel):
    confidence: ConfidenceLevel
    corpus_evidence: list[str] = Field(default_factory=list)
    cross_domain: bool = False
    regulatory_sensitive: bool = False
    security_sensitive: bool = False
    notes: str | None = None


class RequirementAudit(BaseModel):
    approved_by: str
    effective_from: date
    supersedes: str | None = None


class MechanismRequirementSpec(BaseModel):
    fingerprint: str
    matrix_version: str
    families: list[str] = Field(min_length=1)
    requirements: list[CapabilityRequirement] = Field(min_length=1)
    metadata: RequirementMetadata
    audit: RequirementAudit


class MechanismRequirementMatrix(BaseModel):
    matrix_version: str
    specs: list[MechanismRequirementSpec] = Field(min_length=1)
