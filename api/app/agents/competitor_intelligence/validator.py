"""Validation for competitor intelligence LLM output."""

from app.agents.competitor_intelligence.metrics import SENTIMENT_LABEL_RANGES
from app.agents.competitor_intelligence.schemas import (
    CompetitorAnalysisLLMOutput,
    OpportunityCompetitorContext,
)


class CompetitorValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class CompetitorAnalysisValidator:
    """Ensures competitor analysis output is complete and internally consistent."""

    def validate(
        self,
        output: CompetitorAnalysisLLMOutput,
        *,
        context: OpportunityCompetitorContext,
    ) -> CompetitorAnalysisLLMOutput:
        errors: list[str] = []

        if len(output.executive_summary.strip()) < 30:
            errors.append("executive_summary is too short")

        if not output.competitors:
            errors.append("competitors must not be empty")

        if not output.competitive_gaps:
            errors.append("competitive_gaps must not be empty")

        known_products = {product.lower() for product in context.known_products if product.strip()}
        known_products.update(
            product.lower() for product in context.product_mentions if product.strip()
        )

        for index, competitor in enumerate(output.competitors, start=1):
            if len(competitor.name.strip()) < 2:
                errors.append(f"competitors[{index}].name is too short")

            if len(competitor.positioning.strip()) < 15:
                errors.append(f"competitors[{index}].positioning is too short")

            if not competitor.strengths:
                errors.append(f"competitors[{index}].strengths must not be empty")

            if not competitor.weaknesses:
                errors.append(f"competitors[{index}].weaknesses must not be empty")

            if not competitor.customer_complaints:
                errors.append(f"competitors[{index}].customer_complaints must not be empty")

            if len(competitor.pricing.pricing_notes.strip()) < 10:
                errors.append(f"competitors[{index}].pricing.pricing_notes is too short")

            label_range = SENTIMENT_LABEL_RANGES.get(competitor.review_sentiment)
            if label_range is not None:
                low, high = label_range
                if not (low <= competitor.sentiment_score <= high):
                    errors.append(
                        f"competitors[{index}].sentiment_score inconsistent with "
                        f"review_sentiment={competitor.review_sentiment}"
                    )

        if known_products:
            grounded = any(
                any(
                    product in competitor.name.lower() or competitor.name.lower() in product
                    for competitor in output.competitors
                )
                for product in known_products
            )
            if not grounded:
                errors.append("no competitor profile grounded in opportunity evidence products")

        for index, gap in enumerate(output.competitive_gaps, start=1):
            if len(gap.gap.strip()) < 5:
                errors.append(f"competitive_gaps[{index}].gap is too short")
            if len(gap.opportunity_angle.strip()) < 15:
                errors.append(f"competitive_gaps[{index}].opportunity_angle is too short")

        if errors:
            raise CompetitorValidationError(errors)

        return output
