"""Weight constants for executive ranking engine."""

RANKING_ENGINE = "executive_ranking_v1"

DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "pain": 0.20,
    "market": 0.15,
    "revenue": 0.20,
    "competition": 0.15,
    "growth": 0.15,
    "founder_fit": 0.15,
}

MIN_AGENT_COVERAGE = 1
