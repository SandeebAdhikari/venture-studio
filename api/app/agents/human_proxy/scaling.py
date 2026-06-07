"""Canonical score normalization for human proxy LLM output."""

from __future__ import annotations

from app.agents.human_proxy.schemas import HumanProxyLLMOutput

SCORE_FIELD_NAMES = (
    "founder_fit_score",
    "feasibility_score",
    "founder_fit_analysis.score",
    "implementation_feasibility.score",
    "learning_curve.score",
    "execution_complexity.score",
    "capital_requirements.score",
)


class MixedScaleScoreError(Exception):
    """Raised when human proxy scores mix 0–10 and 0–100 scales."""

    def __init__(self, *, decade_fields: list[str], century_fields: list[str]) -> None:
        self.decade_fields = decade_fields
        self.century_fields = century_fields
        message = (
            "mixed-scale human proxy scores detected: "
            f"zero_to_ten fields={decade_fields}, century fields={century_fields}"
        )
        super().__init__(message)


def _collect_scores(output: HumanProxyLLMOutput) -> list[tuple[str, int]]:
    return [
        ("founder_fit_score", output.founder_fit_score),
        ("feasibility_score", output.feasibility_score),
        ("founder_fit_analysis.score", output.founder_fit_analysis.score),
        ("implementation_feasibility.score", output.implementation_feasibility.score),
        ("learning_curve.score", output.learning_curve.score),
        ("execution_complexity.score", output.execution_complexity.score),
        ("capital_requirements.score", output.capital_requirements.score),
    ]


def _scale_score(value: int, *, factor: int) -> int:
    return min(100, value * factor)


def normalize_proxy_scores(
    output: HumanProxyLLMOutput,
) -> tuple[HumanProxyLLMOutput, dict[str, object]]:
    """Normalize all human proxy scores to century scale (0–100).

    Returns the normalized output and scale metadata for auditing.
    """
    scores = _collect_scores(output)
    values = [value for _, value in scores]

    all_decade = all(value <= 10 for value in values)
    all_century = all(value > 10 for value in values)

    if all_decade:
        fields_corrected = [name for name, _ in scores]
        return (
            output.model_copy(
                update={
                    "founder_fit_score": _scale_score(output.founder_fit_score, factor=10),
                    "feasibility_score": _scale_score(output.feasibility_score, factor=10),
                    "founder_fit_analysis": output.founder_fit_analysis.model_copy(
                        update={
                            "score": _scale_score(
                                output.founder_fit_analysis.score,
                                factor=10,
                            )
                        }
                    ),
                    "implementation_feasibility": output.implementation_feasibility.model_copy(
                        update={
                            "score": _scale_score(
                                output.implementation_feasibility.score,
                                factor=10,
                            )
                        }
                    ),
                    "learning_curve": output.learning_curve.model_copy(
                        update={
                            "score": _scale_score(output.learning_curve.score, factor=10),
                        }
                    ),
                    "execution_complexity": output.execution_complexity.model_copy(
                        update={
                            "score": _scale_score(
                                output.execution_complexity.score,
                                factor=10,
                            )
                        }
                    ),
                    "capital_requirements": output.capital_requirements.model_copy(
                        update={
                            "score": _scale_score(
                                output.capital_requirements.score,
                                factor=10,
                            )
                        }
                    ),
                }
            ),
            {
                "scale_detected": "zero_to_ten",
                "scale_factor": 10,
                "fields_corrected": fields_corrected,
            },
        )

    if all_century:
        return output, {
            "scale_detected": "century",
            "scale_factor": 1,
        }

    decade_fields = [name for name, value in scores if value <= 10]
    century_fields = [name for name, value in scores if value > 10]
    raise MixedScaleScoreError(
        decade_fields=decade_fields,
        century_fields=century_fields,
    )
