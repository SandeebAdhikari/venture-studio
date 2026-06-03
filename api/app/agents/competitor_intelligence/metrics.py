"""Deterministic evaluation metrics for competitor analyses."""

from app.agents.competitor_intelligence.schemas import CompetitorAnalysisLLMOutput

SENTIMENT_LABEL_RANGES: dict[str, tuple[float, float]] = {
    "positive": (0.2, 1.0),
    "neutral": (-0.2, 0.2),
    "negative": (-1.0, -0.2),
    "mixed": (-0.5, 0.5),
}


def compute_evaluation_metrics(output: CompetitorAnalysisLLMOutput) -> dict[str, float | int | str]:
    """Derive ranking-friendly metrics from validated competitor analysis output."""
    competitors = output.competitors
    count = len(competitors)
    if count == 0:
        return {
            "competitor_count": 0,
            "avg_sentiment_score": 0.0,
            "negative_sentiment_ratio": 0.0,
            "pricing_transparency_score": 0.0,
            "complaint_density_score": 0.0,
            "differentiation_score": 0.0,
            "threat_score": 0.0,
            "threat_level": "low",
            "competitive_gap_count": len(output.competitive_gaps),
        }

    avg_sentiment = sum(competitor.sentiment_score for competitor in competitors) / count
    negative_ratio = (
        sum(1 for competitor in competitors if competitor.review_sentiment in {"negative", "mixed"})
        / count
    )
    pricing_transparency = (
        sum(
            1
            for competitor in competitors
            if competitor.pricing.starting_price_usd is not None
            or competitor.pricing.model_type != "unknown"
        )
        / count
    )
    complaint_density = (
        sum(len(competitor.customer_complaints) for competitor in competitors) / count
    )
    gaps_count = len(output.competitive_gaps)
    weakness_count = sum(len(competitor.weaknesses) for competitor in competitors)
    differentiation_score = min(1.0, gaps_count * 0.15 + weakness_count * 0.04)

    positive_ratio = (
        sum(1 for competitor in competitors if competitor.review_sentiment == "positive") / count
    )
    avg_strengths = sum(len(competitor.strengths) for competitor in competitors) / count
    threat_score = min(1.0, positive_ratio * 0.5 + avg_strengths * 0.08)

    if threat_score > 0.6:
        threat_level = "high"
    elif threat_score > 0.3:
        threat_level = "medium"
    else:
        threat_level = "low"

    return {
        "competitor_count": count,
        "avg_sentiment_score": round(avg_sentiment, 3),
        "negative_sentiment_ratio": round(negative_ratio, 3),
        "pricing_transparency_score": round(pricing_transparency, 3),
        "complaint_density_score": round(min(1.0, complaint_density / 5.0), 3),
        "differentiation_score": round(differentiation_score, 3),
        "threat_score": round(threat_score, 3),
        "threat_level": threat_level,
        "competitive_gap_count": gaps_count,
    }
