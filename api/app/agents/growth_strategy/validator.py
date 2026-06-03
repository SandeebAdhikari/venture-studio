"""Validation for growth strategy LLM output."""

from app.agents.growth_strategy.schemas import GrowthStrategyLLMOutput, OpportunityGrowthContext


class GrowthStrategyValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class GrowthStrategyValidator:
    """Ensures growth strategy output is complete and consistent."""

    def validate(
        self,
        output: GrowthStrategyLLMOutput,
        *,
        context: OpportunityGrowthContext,
    ) -> GrowthStrategyLLMOutput:
        errors: list[str] = []
        max_complaint_index = len(context.complaint_evidence) - 1

        if len(output.executive_summary.strip()) < 50:
            errors.append("executive_summary is too short")

        if output.growth_score >= 80 and output.scalability_score < 40:
            errors.append("high growth_score requires scalability_score >= 40")

        if output.growth_score >= 80 and output.risk_score >= 80:
            errors.append("high growth_score is inconsistent with very high risk_score")

        for index, item in enumerate(output.supporting_evidence, start=1):
            if len(item.excerpt.strip()) < 10:
                errors.append(f"supporting_evidence[{index}].excerpt is too short")
            if item.complaint_index is not None:
                if item.complaint_index < 0 or item.complaint_index > max_complaint_index:
                    errors.append(f"supporting_evidence[{index}].complaint_index out of range")

        for index, phase in enumerate(output.growth_phases, start=1):
            if len(phase.focus.strip()) < 10:
                errors.append(f"growth_phases[{index}].focus is too short")

        if errors:
            raise GrowthStrategyValidationError(errors)

        return output
