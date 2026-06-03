"""Validation for product strategy LLM output."""

from app.agents.product_strategy.schemas import OpportunityPlanningContext, ProductStrategyLLMOutput


class ProductStrategyValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class ProductStrategyValidator:
    """Ensures product strategy output is complete and consistent."""

    def validate(
        self,
        output: ProductStrategyLLMOutput,
        *,
        context: OpportunityPlanningContext,
    ) -> ProductStrategyLLMOutput:
        errors: list[str] = []
        max_complaint_index = len(context.complaint_evidence) - 1

        if len(output.mvp_definition.strip()) < 30:
            errors.append("mvp_definition is too short")

        if len(output.executive_summary.strip()) < 30:
            errors.append("executive_summary is too short")

        ranks = [item.rank for item in output.feature_priorities]
        if len(ranks) != len(set(ranks)):
            errors.append("feature_priorities ranks must be unique")

        phase_weeks = sum(phase.duration_weeks for phase in output.development_phases)
        if output.estimated_timeline.total_weeks < phase_weeks:
            errors.append("estimated_timeline.total_weeks must cover all phase durations")

        if output.estimated_timeline.mvp_weeks > output.estimated_timeline.total_weeks:
            errors.append("estimated_timeline.mvp_weeks cannot exceed total_weeks")

        priority_names = {item.feature_name for item in output.feature_priorities}
        feature_names = {item.name for item in output.core_features}
        unknown_priorities = priority_names - feature_names
        if unknown_priorities:
            errors.append(
                "feature_priorities reference unknown features: "
                + ", ".join(sorted(unknown_priorities))
            )

        for index, feature in enumerate(output.core_features, start=1):
            if len(feature.description.strip()) < 15:
                errors.append(f"core_features[{index}].description is too short")
            if len(feature.user_value.strip()) < 10:
                errors.append(f"core_features[{index}].user_value is too short")

        for index, phase in enumerate(output.development_phases, start=1):
            if len(phase.phase_name.strip()) < 3:
                errors.append(f"development_phases[{index}].phase_name is too short")

        for index, risk in enumerate(output.technical_risks, start=1):
            if len(risk.mitigation.strip()) < 10:
                errors.append(f"technical_risks[{index}].mitigation is too short")

        for index, item in enumerate(output.supporting_evidence, start=1):
            if len(item.excerpt.strip()) < 10:
                errors.append(f"supporting_evidence[{index}].excerpt is too short")
            if item.complaint_index is not None:
                if item.complaint_index < 0 or item.complaint_index > max_complaint_index:
                    errors.append(f"supporting_evidence[{index}].complaint_index out of range")

        if errors:
            raise ProductStrategyValidationError(errors)

        return output
