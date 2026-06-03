"""Validation for revenue validation LLM output."""

from app.agents.revenue_validation.schemas import (
    OpportunityRevenueContext,
    RevenueValidationLLMOutput,
)


class RevenueValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class RevenueValidationValidator:
    """Ensures revenue validation output is complete and consistent."""

    def validate(
        self,
        output: RevenueValidationLLMOutput,
        *,
        context: OpportunityRevenueContext,
    ) -> RevenueValidationLLMOutput:
        errors: list[str] = []
        max_complaint_index = len(context.complaint_evidence) - 1
        max_competitor_index = len(context.competitor_pricing) - 1

        if len(output.executive_summary.strip()) < 30:
            errors.append("executive_summary is too short")

        if output.willingness_to_pay_score >= 70 and output.revenue_confidence_score < 30:
            errors.append("high willingness_to_pay_score requires revenue_confidence_score >= 30")

        for index, recommendation in enumerate(output.pricing_recommendations, start=1):
            if len(recommendation.rationale.strip()) < 15:
                errors.append(f"pricing_recommendations[{index}].rationale is too short")
            if recommendation.price_usd < 0:
                errors.append(f"pricing_recommendations[{index}].price_usd must be >= 0")

        for index, profile in enumerate(output.buyer_profiles, start=1):
            if len(profile.existing_spending_notes.strip()) < 10:
                errors.append(f"buyer_profiles[{index}].existing_spending_notes is too short")
            if len(profile.purchasing_frequency.strip()) < 5:
                errors.append(f"buyer_profiles[{index}].purchasing_frequency is too short")

        for index, item in enumerate(output.supporting_evidence, start=1):
            if len(item.excerpt.strip()) < 10:
                errors.append(f"supporting_evidence[{index}].excerpt is too short")
            if item.complaint_index is not None:
                if item.complaint_index < 0 or item.complaint_index > max_complaint_index:
                    errors.append(f"supporting_evidence[{index}].complaint_index out of range")
            if item.competitor_index is not None:
                if item.competitor_index < 0 or item.competitor_index > max_competitor_index:
                    errors.append(f"supporting_evidence[{index}].competitor_index out of range")

        if context.competitor_pricing:
            has_competitor_evidence = any(
                item.evidence_type == "competitor_pricing" for item in output.supporting_evidence
            )
            if not has_competitor_evidence:
                errors.append(
                    "supporting_evidence must include competitor_pricing when competitors exist"
                )

        if errors:
            raise RevenueValidationError(errors)

        return output
