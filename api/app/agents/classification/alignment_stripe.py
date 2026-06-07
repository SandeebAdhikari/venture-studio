"""Stripe Billing neighborhood alignment examples."""

from __future__ import annotations

from app.agents.classification.alignment_preamble import alignment_namespace_preamble


def alignment_stripe_prompt_block() -> str:
    return (
        f"{alignment_namespace_preamble()}"
        "The seed category 'pricing' already covers billing cost and payment-processor frustration.\n\n"
        "problem_category mapping guidance (Stripe Billing neighborhood):\n"
        "- Payment processor fees, billing cost frustration, Stripe access/pricing issues → pricing\n"
        "- Fraud, risk controls, account bans, high-risk classification, Radar blocks → security\n"
        "- Missing billing capabilities Stripe/tools lack → missing_feature\n"
        "- Invoice collection, late payments, billing ops workflow friction → workflow\n\n"
        "Founder signal examples (problem_category | business_function_code | jtbd_code | consequence_code):\n"
        '- "Kicked off Stripe; classified as high risk." → security | payment_processor | accept_payments | revenue_interruption\n'
        '- "Stripe billing fees are killing margins." → pricing | payment_processor | accept_payments | margin_erosion\n'
        '- "We need usage-based billing support Stripe lacks." → missing_feature | subscription_management | manage_subscriptions | revenue_interruption\n'
        '- "Clients never pay invoices on time." → workflow | invoice_collection | collect_invoices | revenue_interruption\n'
        '- WRONG: problem_category=billing or problem_category=billing_operations (always invalid)\n'
        '- RIGHT: problem_category=pricing with business_function_code=billing_operations when ops automation is the pain\n'
    )
