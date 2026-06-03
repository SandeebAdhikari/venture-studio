"""Validation for market research LLM output."""

from app.agents.market_research.schemas import MarketResearchLLMOutput


class MarketResearchValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class MarketResearchValidator:
    """Ensures market intelligence output is internally consistent."""

    def validate(self, output: MarketResearchLLMOutput) -> MarketResearchLLMOutput:
        errors: list[str] = []

        if len(output.executive_summary.strip()) < 30:
            errors.append("executive_summary is too short")

        if output.sam_usd > output.tam_usd:
            errors.append("sam_usd must not exceed tam_usd")

        if output.tam_usd > output.market_size_usd:
            errors.append("tam_usd must not exceed market_size_usd")

        if not output.customer_segments:
            errors.append("customer_segments must not be empty")

        if not output.industry_trends:
            errors.append("industry_trends must not be empty")

        if not output.supporting_evidence:
            errors.append("supporting_evidence must not be empty")

        for index, segment in enumerate(output.customer_segments, start=1):
            if len(segment.name.strip()) < 2:
                errors.append(f"customer_segments[{index}].name is too short")
            if len(segment.description.strip()) < 10:
                errors.append(f"customer_segments[{index}].description is too short")

        for index, trend in enumerate(output.industry_trends, start=1):
            if len(trend.trend.strip()) < 5:
                errors.append(f"industry_trends[{index}].trend is too short")
            if len(trend.relevance.strip()) < 10:
                errors.append(f"industry_trends[{index}].relevance is too short")

        for index, evidence in enumerate(output.supporting_evidence, start=1):
            if len(evidence.claim.strip()) < 10:
                errors.append(f"supporting_evidence[{index}].claim is too short")
            if len(evidence.source_reference.strip()) < 5:
                errors.append(f"supporting_evidence[{index}].source_reference is too short")

        if errors:
            raise MarketResearchValidationError(errors)

        return output
