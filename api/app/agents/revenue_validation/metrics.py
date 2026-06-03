"""Deterministic evaluation metrics for revenue validation."""

from app.agents.revenue_validation.schemas import RevenueValidationLLMOutput


def compute_evaluation_metrics(output: RevenueValidationLLMOutput) -> dict[str, float | int]:
    prices = [rec.price_usd for rec in output.pricing_recommendations if rec.price_usd >= 0]
    avg_price = sum(prices) / len(prices) if prices else 0.0
    competitor_refs = sum(
        1 for item in output.supporting_evidence if item.evidence_type == "competitor_pricing"
    )
    evidence_count = len(output.supporting_evidence)

    evaluation_readiness = min(
        100,
        int(
            output.revenue_confidence_score * 0.45
            + output.willingness_to_pay_score * 0.35
            + min(evidence_count, 8) * 2.5
            + min(len(output.pricing_recommendations), 3) * 5
        ),
    )

    return {
        "willingness_to_pay_score": output.willingness_to_pay_score,
        "revenue_confidence_score": output.revenue_confidence_score,
        "pricing_recommendation_count": len(output.pricing_recommendations),
        "buyer_profile_count": len(output.buyer_profiles),
        "evidence_count": evidence_count,
        "competitor_pricing_reference_count": competitor_refs,
        "avg_recommended_price_usd": round(avg_price, 2),
        "evaluation_readiness_score": evaluation_readiness,
    }
