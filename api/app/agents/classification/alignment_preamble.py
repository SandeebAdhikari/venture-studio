"""Shared preamble for problem_category vs founder signal namespace alignment."""

from __future__ import annotations


def alignment_namespace_preamble() -> str:
    return (
        "IMPORTANT — two separate code namespaces:\n"
        "1) problem_category = complaint THEME (pricing, security, missing_feature, …)\n"
        "2) founder signals = business_function_code, jtbd_code, consequence_code\n"
        "Never put founder signal codes into problem_category.\n"
        "problem_category must NEVER be 'billing' or 'billing_operations'.\n"
        "The word 'billing' in user text is natural language — map it to a valid problem_category code.\n"
        "The code 'billing_operations' is ONLY valid as business_function_code, never problem_category.\n"
    )
