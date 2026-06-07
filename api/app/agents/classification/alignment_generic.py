"""Generic fallback alignment when neighborhood is unknown."""

from __future__ import annotations

from app.agents.classification.alignment_preamble import alignment_namespace_preamble


def alignment_generic_prompt_block() -> str:
    return (
        f"{alignment_namespace_preamble()}"
        "Choose founder signals that match the buyer's business function — not product buzzwords.\n\n"
        "Cross-neighborhood negative examples:\n"
        '- GPU/compute rental frustration → NOT payment_processor | accept_payments\n'
        '- MCP/agent tooling → NOT manage_subscriptions (unless true SaaS subscription billing)\n'
        '- Security vulnerability disclosure → NOT fraud_prevention | prevent_fraud\n'
        '- Stripe/processor/billing pain → use payment_processor, billing_operations, etc.\n'
    )
