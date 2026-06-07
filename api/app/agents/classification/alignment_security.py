"""Security neighborhood alignment examples."""

from __future__ import annotations

from app.agents.classification.alignment_preamble import alignment_namespace_preamble


def alignment_security_prompt_block() -> str:
    return (
        f"{alignment_namespace_preamble()}"
        "Security neighborhood — use native security founder signals, NOT payments fraud codes.\n\n"
        "problem_category mapping guidance:\n"
        "- Vulnerability reports, disclosure retaliation, unpatched flaws → security\n"
        "- Breach, ransomware, incident negligence → security\n"
        "- Session fixation, auth flaws, appsec issues → security\n"
        "- OAuth/MFA/identity friction → security or missing_feature\n\n"
        "Founder signal examples (problem_category | business_function_code | jtbd_code | consequence_code):\n"
        '- "Reprimanded for reporting a security vulnerability." → security | vulnerability_management | remediate_vulnerabilities | trust_erosion\n'
        '- "Ransomware attack; employer negligent with patient data." → security | incident_response | respond_to_incidents | trust_erosion\n'
        '- "Session ID is the user\'s email — session fixation." → security | application_security | secure_applications | operational_risk\n'
        '- "Easily-guessable URL exposes password file on deployed page." → security | vulnerability_management | remediate_vulnerabilities | operational_risk\n\n'
        "NEGATIVE examples — do NOT use these for security complaints:\n"
        '- WRONG: fraud_prevention | prevent_fraud (payments fraud only — Stripe neighborhood)\n'
        '- WRONG: payment_processor | accept_payments\n'
        '- WRONG: observability | monitor_systems (unless purely uptime monitoring with no security wedge)\n'
    )
