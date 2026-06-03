"""Deterministic validation metrics for customer research."""

from app.agents.customer_research.schemas import CustomerResearchLLMOutput, OpportunityCustomerContext

SENTIMENT_LABEL_RANGES: dict[str, tuple[float, float]] = {
    "positive": (0.2, 1.0),
    "neutral": (-0.2, 0.2),
    "negative": (-1.0, -0.2),
    "mixed": (-0.5, 0.5),
}


def compute_validation_metrics(
    output: CustomerResearchLLMOutput,
    *,
    context: OpportunityCustomerContext,
    linked_complaint_count: int,
) -> dict[str, float | int | str]:
    """Derive validation-layer metrics from customer research output."""
    evidence_count = len(output.supporting_evidence)
    evidence_types = {item.evidence_type for item in output.supporting_evidence}
    source_diversity = len(evidence_types) / 5.0

    complaint_count = len(context.complaint_evidence)
    complaint_coverage = (
        linked_complaint_count / complaint_count if complaint_count else 0.0
    )

    avg_severity = 0.0
    if output.representative_complaints:
        avg_severity = sum(item.severity for item in output.representative_complaints) / len(
            output.representative_complaints
        )

    demand_score = round(
        output.pain_score * 0.35
        + output.urgency_score * 0.30
        + output.frequency_score * 0.25
        + max(0.0, -output.sentiment_score) * 50 * 0.10,
    )
    validation_readiness = min(
        100,
        int(
            demand_score * 0.5
            + complaint_coverage * 100 * 0.2
            + source_diversity * 100 * 0.15
            + min(evidence_count, 10) * 1.5
        ),
    )

    return {
        "cares_verdict": output.cares_verdict,
        "demand_score": demand_score,
        "evidence_count": evidence_count,
        "linked_complaint_count": linked_complaint_count,
        "source_type_diversity": round(source_diversity, 3),
        "complaint_coverage": round(complaint_coverage, 3),
        "avg_representative_severity": round(avg_severity, 2),
        "validation_readiness_score": validation_readiness,
    }
