"""Heuristic weights for opportunity scoring (no external market research)."""

# Category implementation ease: higher = easier for a solo founder to ship V1.
CATEGORY_IMPLEMENTATION_EASE: dict[str, float] = {
    "onboarding": 0.90,
    "ux_ui": 0.85,
    "workflow": 0.80,
    "missing_feature": 0.75,
    "support": 0.70,
    "data_export": 0.65,
    "integration": 0.55,
    "performance": 0.50,
    "pricing": 0.60,
    "security": 0.40,
    "other": 0.55,
}

# Domain implementation ease without market research — complexity proxy only.
DOMAIN_IMPLEMENTATION_EASE: dict[str, float] = {
    "saas_b2b": 0.85,
    "saas_b2c": 0.75,
    "devtools": 0.90,
    "creator_economy": 0.80,
    "marketing": 0.75,
    "ops_it": 0.70,
    "hr_recruiting": 0.65,
    "ecommerce": 0.60,
    "education": 0.55,
    "fintech": 0.35,
    "healthcare": 0.30,
    "other": 0.50,
}

# Solo-founder fit by domain (internal heuristic, not market sizing).
FOUNDER_FIT_DOMAIN: dict[str, float] = {
    "saas_b2b": 0.90,
    "devtools": 0.95,
    "creator_economy": 0.85,
    "marketing": 0.80,
    "ops_it": 0.75,
    "saas_b2c": 0.70,
    "hr_recruiting": 0.65,
    "ecommerce": 0.60,
    "education": 0.55,
    "fintech": 0.40,
    "healthcare": 0.35,
    "other": 0.50,
}

FOUNDER_FIT_PERSONAS: frozenset[str] = frozenset(
    {"founder", "developer", "product_manager", "ops_admin"}
)

DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "volume": 0.25,
    "severity": 0.20,
    "market_indicators": 0.20,
    "implementation_ease": 0.20,
    "founder_fit": 0.15,
}
