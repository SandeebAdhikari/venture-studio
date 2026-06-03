"""Score computation for generated opportunities."""

from app.agents.opportunity.schemas import ComplaintPattern


def compute_opportunity_scores(
    pattern: ComplaintPattern,
    *,
    confidence_score: float,
    min_cluster_size: int,
) -> dict[str, float]:
    """Derive ranking scores from pattern statistics (no market research)."""
    frequency_score = min(1.0, pattern.complaint_count / 100)
    severity_score = min(1.0, pattern.avg_severity / 5)
    evidence_score = min(1.0, pattern.complaint_count / max(min_cluster_size, 1))
    overall_score = round(
        0.35 * confidence_score
        + 0.30 * frequency_score
        + 0.20 * severity_score
        + 0.15 * evidence_score,
        4,
    )
    return {
        "overall_score": overall_score,
        "confidence_score": confidence_score,
        "frequency_score": round(frequency_score, 4),
        "severity_score": round(severity_score, 4),
        "evidence_score": round(evidence_score, 4),
    }
