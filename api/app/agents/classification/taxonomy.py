"""Classification taxonomy codes aligned with MVP documentation."""

PROBLEM_CATEGORIES: frozenset[str] = frozenset(
    {
        "pricing",
        "integration",
        "ux_ui",
        "performance",
        "support",
        "missing_feature",
        "workflow",
        "data_export",
        "onboarding",
        "security",
        "other",
    }
)

INDUSTRIES: frozenset[str] = frozenset(
    {
        "saas_b2b",
        "saas_b2c",
        "ecommerce",
        "devtools",
        "fintech",
        "healthcare",
        "education",
        "hr_recruiting",
        "marketing",
        "ops_it",
        "creator_economy",
        "other",
    }
)

CUSTOMER_TYPES: frozenset[str] = frozenset(
    {
        "founder",
        "developer",
        "product_manager",
        "ops_admin",
        "marketer",
        "sales",
        "support_agent",
        "consumer",
        "other",
    }
)


def taxonomy_prompt_block() -> str:
    return (
        f"problem_category must be one of: {', '.join(sorted(PROBLEM_CATEGORIES))}\n"
        f"industry must be one of: {', '.join(sorted(INDUSTRIES))}\n"
        f"customer_type must be one of: {', '.join(sorted(CUSTOMER_TYPES))}\n"
        "severity_score must be an integer from 1 (mild) to 5 (blocker)."
    )
