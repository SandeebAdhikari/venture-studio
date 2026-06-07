"""Founder signal neighborhood routing for classification prompts."""

from __future__ import annotations

from enum import StrEnum

from app.config import Settings
from app.schemas.pipeline import PipelineRunOptions


class FounderSignalNeighborhood(StrEnum):
    STRIPE_BILLING = "stripe_billing"
    SECURITY = "security"
    DEVTOOLS = "devtools"
    AI_INFRASTRUCTURE = "ai_infrastructure"
    GENERIC = "generic"


_CORPUS_ALIASES: dict[str, FounderSignalNeighborhood] = {
    "stripe": FounderSignalNeighborhood.STRIPE_BILLING,
    "stripe_billing": FounderSignalNeighborhood.STRIPE_BILLING,
    "stripe-billing": FounderSignalNeighborhood.STRIPE_BILLING,
    "security": FounderSignalNeighborhood.SECURITY,
    "security-corpus-validation": FounderSignalNeighborhood.SECURITY,
    "devtools": FounderSignalNeighborhood.DEVTOOLS,
    "devtools_v1": FounderSignalNeighborhood.DEVTOOLS,
    "devtools-v1": FounderSignalNeighborhood.DEVTOOLS,
    "ai_infrastructure": FounderSignalNeighborhood.AI_INFRASTRUCTURE,
    "ai_infrastructure_v1": FounderSignalNeighborhood.AI_INFRASTRUCTURE,
    "ai-infrastructure": FounderSignalNeighborhood.AI_INFRASTRUCTURE,
    "ai-infrastructure-v1": FounderSignalNeighborhood.AI_INFRASTRUCTURE,
}


def normalize_neighborhood(value: str | None) -> FounderSignalNeighborhood | None:
    if value is None or not str(value).strip():
        return None
    key = str(value).strip().lower().replace(" ", "_")
    return _CORPUS_ALIASES.get(key)


def resolve_neighborhood(
    *,
    explicit: str | FounderSignalNeighborhood | None = None,
    pipeline_options: PipelineRunOptions | None = None,
    settings: Settings | None = None,
) -> FounderSignalNeighborhood:
    """Resolve neighborhood for classification; defaults to Stripe for backward compatibility."""
    for candidate in (
        explicit,
        pipeline_options.founder_signal_neighborhood if pipeline_options else None,
        settings.founder_signal_neighborhood if settings else None,
    ):
        resolved = (
            candidate
            if isinstance(candidate, FounderSignalNeighborhood)
            else normalize_neighborhood(candidate if isinstance(candidate, str) else None)
        )
        if resolved is not None:
            return resolved
    return FounderSignalNeighborhood.STRIPE_BILLING
