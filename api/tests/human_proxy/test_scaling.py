"""Unit tests for human proxy score normalization."""

import pytest

from app.agents.human_proxy.mock_client import default_mock_human_proxy_output
from app.agents.human_proxy.scaling import (
    SCORE_FIELD_NAMES,
    MixedScaleScoreError,
    normalize_proxy_scores,
)
from app.agents.human_proxy.schemas import (
    CapitalRequirementsOutput,
    ExecutionComplexityOutput,
    FounderFitAnalysisOutput,
    HumanProxyLLMOutput,
    ImplementationFeasibilityOutput,
    LearningCurveOutput,
    ProxyEvidenceOutput,
)


def _zero_to_ten_output(
    *,
    founder_fit_score: int = 8,
    feasibility_score: int = 7,
    analysis_score: int = 8,
    feasibility_analysis_score: int = 7,
    learning_curve_score: int = 4,
    execution_complexity_score: int = 5,
    capital_requirements_score: int = 7,
) -> HumanProxyLLMOutput:
    return HumanProxyLLMOutput(
        founder_fit_score=founder_fit_score,
        feasibility_score=feasibility_score,
        recommendation="explore",
        founder_fit_analysis=FounderFitAnalysisOutput(
            score=analysis_score,
            skill_matches=["Python"],
            skill_gaps=["Mobile"],
            rationale="Moderate fit on a zero-to-ten scale.",
        ),
        implementation_feasibility=ImplementationFeasibilityOutput(
            score=feasibility_analysis_score,
            build_complexity="medium",
            rationale="Buildable with familiar tooling.",
            blockers=["Compliance review"],
        ),
        learning_curve=LearningCurveOutput(
            score=learning_curve_score,
            difficulty="medium",
            new_skills_required=["Domain expertise"],
            rationale="Some new skills required.",
        ),
        execution_complexity=ExecutionComplexityOutput(
            score=execution_complexity_score,
            complexity_level="medium",
            operational_burden="Moderate support load",
            rationale="Operational burden is manageable.",
        ),
        capital_requirements=CapitalRequirementsOutput(
            score=capital_requirements_score,
            estimated_monthly_usd="$100-$300",
            bootstrap_friendly=True,
            rationale="Bootstrap-friendly spend profile.",
        ),
        supporting_evidence=[
            ProxyEvidenceOutput(
                evidence_type="skill_signal",
                excerpt="Founder skills align with the core web stack.",
                source_reference="Founder profile",
                supports_conclusion="founder_fit",
                confidence="high",
            )
        ],
        executive_summary=(
            "Moderate founder fit on a zero-to-ten scale with manageable feasibility "
            "and execution complexity for a solo technical founder."
        ),
    )


def test_normalize_uniform_zero_to_ten_input() -> None:
    output = _zero_to_ten_output()

    normalized, metadata = normalize_proxy_scores(output)

    assert normalized.founder_fit_score == 80
    assert normalized.feasibility_score == 70
    assert normalized.founder_fit_analysis.score == 80
    assert normalized.implementation_feasibility.score == 70
    assert normalized.learning_curve.score == 40
    assert normalized.execution_complexity.score == 50
    assert normalized.capital_requirements.score == 70
    assert metadata == {
        "scale_detected": "zero_to_ten",
        "scale_factor": 10,
        "fields_corrected": list(SCORE_FIELD_NAMES),
    }


def test_normalize_uniform_century_input() -> None:
    output = default_mock_human_proxy_output()

    normalized, metadata = normalize_proxy_scores(output)

    assert normalized == output
    assert metadata == {
        "scale_detected": "century",
        "scale_factor": 1,
    }


def test_normalize_rejects_mixed_scale_input() -> None:
    output = default_mock_human_proxy_output()
    output.feasibility_score = 7

    with pytest.raises(MixedScaleScoreError) as exc_info:
        normalize_proxy_scores(output)

    assert exc_info.value.decade_fields == ["feasibility_score"]
    assert "founder_fit_score" in exc_info.value.century_fields
    assert "mixed-scale human proxy scores detected" in str(exc_info.value)


def test_normalize_is_idempotent_for_century_input() -> None:
    output = default_mock_human_proxy_output()

    first, first_metadata = normalize_proxy_scores(output)
    second, second_metadata = normalize_proxy_scores(first)

    assert second == first == output
    assert first_metadata == second_metadata == {
        "scale_detected": "century",
        "scale_factor": 1,
    }


def test_normalize_is_stable_after_zero_to_ten_conversion() -> None:
    output = _zero_to_ten_output()

    first, first_metadata = normalize_proxy_scores(output)
    second, second_metadata = normalize_proxy_scores(first)

    assert second == first
    assert first_metadata["scale_detected"] == "zero_to_ten"
    assert second_metadata == {
        "scale_detected": "century",
        "scale_factor": 1,
    }


def test_normalize_preserves_nested_score_consistency() -> None:
    output = _zero_to_ten_output(
        founder_fit_score=8,
        analysis_score=7,
    )

    normalized, _metadata = normalize_proxy_scores(output)

    assert normalized.founder_fit_score - normalized.founder_fit_analysis.score == 10
    assert normalized.founder_fit_score == 80
    assert normalized.founder_fit_analysis.score == 70
