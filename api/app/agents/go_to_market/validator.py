"""Validation for go-to-market LLM output."""

from app.agents.go_to_market.grounding import normalize_evidence_indices
from app.agents.go_to_market.schemas import GoToMarketLLMOutput, OpportunityGTMContext


class GoToMarketValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class GoToMarketValidator:
    """Ensures GTM output is complete and consistent."""

    def validate(
        self,
        output: GoToMarketLLMOutput,
        *,
        context: OpportunityGTMContext,
    ) -> GoToMarketLLMOutput:
        output = normalize_evidence_indices(output, context)
        errors: list[str] = []
        max_complaint_index = len(context.complaint_evidence) - 1

        if len(output.gtm_report.strip()) < 50:
            errors.append("gtm_report is too short")

        if len(output.ideal_customer_profile.summary.strip()) < 20:
            errors.append("ideal_customer_profile.summary is too short")

        if output.confidence_score >= 75 and output.estimated_cac_usd <= 0:
            errors.append("high confidence_score requires estimated_cac_usd > 0")

        phase_weeks = sum(phase.duration_weeks for phase in output.acquisition_phases)
        if phase_weeks < 1:
            errors.append("acquisition_phases must include at least one week")

        channel_names = {channel.channel_name for channel in output.acquisition_channels}
        if len(channel_names) != len(output.acquisition_channels):
            errors.append("acquisition_channels must have unique channel_name values")

        for index, persona in enumerate(output.customer_personas, start=1):
            if len(persona.role.strip()) < 3:
                errors.append(f"customer_personas[{index}].role is too short")

        for index, channel in enumerate(output.acquisition_channels, start=1):
            if len(channel.rationale.strip()) < 15:
                errors.append(f"acquisition_channels[{index}].rationale is too short")

        for index, item in enumerate(output.supporting_evidence, start=1):
            if len(item.excerpt.strip()) < 10:
                errors.append(f"supporting_evidence[{index}].excerpt is too short")
            if item.complaint_index is not None:
                if item.complaint_index < 0 or item.complaint_index > max_complaint_index:
                    errors.append(f"supporting_evidence[{index}].complaint_index out of range")

        if errors:
            raise GoToMarketValidationError(errors)

        return output
