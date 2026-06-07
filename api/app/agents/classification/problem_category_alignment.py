"""Problem category namespace alignment and lightweight normalization."""

from __future__ import annotations

from app.agents.classification.alignment_ai_infrastructure import (
    alignment_ai_infrastructure_prompt_block,
)
from app.agents.classification.alignment_devtools import alignment_devtools_prompt_block
from app.agents.classification.alignment_generic import alignment_generic_prompt_block
from app.agents.classification.alignment_security import alignment_security_prompt_block
from app.agents.classification.alignment_stripe import alignment_stripe_prompt_block
from app.agents.classification.neighborhood import (
    FounderSignalNeighborhood,
    normalize_neighborhood,
    resolve_neighborhood,
)
from app.agents.classification.taxonomy import PROBLEM_CATEGORIES

INVALID_PROBLEM_CATEGORY_ALIASES: frozenset[str] = frozenset({"billing", "billing_operations"})

_SECURITY_HINTS: frozenset[str] = frozenset(
    {
        "kicked off",
        "high risk",
        "classified as high risk",
        "deplatform",
        "account suspended",
        "account ban",
        "blocked by stripe-radar",
        "stripe-radar",
    }
)

_MISSING_FEATURE_HINTS: frozenset[str] = frozenset(
    {
        "does not support",
        "doesn't support",
        "does not allow",
        "doesn't allow",
        "not allow me to",
        "usage-based",
        "usage based",
        "track usage",
        "capability",
        "missing feature",
    }
)

_WORKFLOW_HINTS: frozenset[str] = frozenset(
    {
        "invoice",
        "invoices",
        "pay on time",
        "never pays",
        "collections",
        "recurring billing setup",
        "end of the month",
        "payment operations",
    }
)


def alignment_prompt_for_neighborhood(neighborhood: FounderSignalNeighborhood) -> str:
    """Return neighborhood-specific alignment examples."""
    blocks = {
        FounderSignalNeighborhood.STRIPE_BILLING: alignment_stripe_prompt_block,
        FounderSignalNeighborhood.SECURITY: alignment_security_prompt_block,
        FounderSignalNeighborhood.DEVTOOLS: alignment_devtools_prompt_block,
        FounderSignalNeighborhood.AI_INFRASTRUCTURE: alignment_ai_infrastructure_prompt_block,
        FounderSignalNeighborhood.GENERIC: alignment_generic_prompt_block,
    }
    return blocks[neighborhood]()


def alignment_prompt_block(
    neighborhood: FounderSignalNeighborhood | str | None = None,
) -> str:
    """Prompt guidance separating problem_category from founder signal namespaces."""
    if isinstance(neighborhood, FounderSignalNeighborhood):
        resolved = neighborhood
    else:
        resolved = resolve_neighborhood(explicit=normalize_neighborhood(neighborhood))
    return alignment_prompt_for_neighborhood(resolved)


def _classification_text(*, title: str = "", summary: str = "", verbatim_quote: str = "") -> str:
    return " ".join(part for part in (title, summary, verbatim_quote) if part).lower()


def normalize_problem_category(
    code: str,
    *,
    title: str = "",
    summary: str = "",
    verbatim_quote: str = "",
) -> str:
    """Remap common LLM namespace leaks before taxonomy validation."""
    normalized = code.strip().lower()
    if normalized in PROBLEM_CATEGORIES:
        return normalized

    text = _classification_text(title=title, summary=summary, verbatim_quote=verbatim_quote)

    if normalized == "billing":
        if any(hint in text for hint in _SECURITY_HINTS):
            return "security"
        if any(hint in text for hint in _MISSING_FEATURE_HINTS):
            return "missing_feature"
        if any(hint in text for hint in _WORKFLOW_HINTS):
            return "workflow"
        return "pricing"

    if normalized == "billing_operations":
        if any(hint in text for hint in _MISSING_FEATURE_HINTS):
            return "missing_feature"
        if any(hint in text for hint in _SECURITY_HINTS):
            return "security"
        if any(hint in text for hint in _WORKFLOW_HINTS):
            return "workflow"
        return "workflow"

    return code
