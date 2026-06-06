"""Problem category namespace alignment and lightweight normalization."""

from __future__ import annotations

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


def alignment_prompt_block() -> str:
    """Prompt guidance separating problem_category from founder signal namespaces."""
    return (
        "IMPORTANT — two separate code namespaces:\n"
        "1) problem_category = complaint THEME (pricing, security, missing_feature, …)\n"
        "2) founder signals = business_function_code, jtbd_code, consequence_code\n"
        "Never put founder signal codes into problem_category.\n"
        "problem_category must NEVER be 'billing' or 'billing_operations'.\n"
        "The word 'billing' in user text is natural language — map it to a valid problem_category code.\n"
        "The code 'billing_operations' is ONLY valid as business_function_code, never problem_category.\n"
        "The seed category 'pricing' already covers billing cost and payment-processor frustration.\n\n"
        "problem_category mapping guidance:\n"
        "- Payment processor fees, billing cost frustration, Stripe access/pricing issues → pricing\n"
        "- Fraud, risk controls, account bans, high-risk classification, Radar blocks → security\n"
        "- Missing billing capabilities Stripe/tools lack → missing_feature\n"
        "- Invoice collection, late payments, billing ops workflow friction → workflow\n\n"
        "Examples (problem_category | business_function_code | jtbd_code | consequence_code):\n"
        '- "Kicked off Stripe; classified as high risk." → security | payment_processor | accept_payments | revenue_interruption\n'
        '- "Stripe billing fees are killing margins." → pricing | payment_processor | accept_payments | margin_erosion\n'
        '- "We need usage-based billing support Stripe lacks." → missing_feature | subscription_management | manage_subscriptions | revenue_interruption\n'
        '- "Clients never pay invoices on time." → workflow | invoice_collection | collect_invoices | revenue_interruption\n'
        '- WRONG: problem_category=billing or problem_category=billing_operations (always invalid)\n'
        '- RIGHT: problem_category=pricing with business_function_code=billing_operations when ops automation is the pain\n'
    )


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
