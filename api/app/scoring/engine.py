"""Deterministic opportunity scoring engine."""

from app.scoring.constants import (
    CATEGORY_IMPLEMENTATION_EASE,
    DEFAULT_DIMENSION_WEIGHTS,
    DOMAIN_IMPLEMENTATION_EASE,
    FOUNDER_FIT_DOMAIN,
    FOUNDER_FIT_PERSONAS,
)
from app.scoring.schemas import DimensionScores, ScoringInput, ScoringResult

SCORING_MODEL = "scoring_engine_v1"


class OpportunityScoringEngine:
    """Scores opportunities 0–100 from complaint evidence (no market research)."""

    def __init__(
        self,
        *,
        volume_target: int = 50,
        dimension_weights: dict[str, float] | None = None,
    ) -> None:
        self._volume_target = max(volume_target, 1)
        self._weights = dimension_weights or DEFAULT_DIMENSION_WEIGHTS

    def score(self, data: ScoringInput) -> ScoringResult:
        dimensions = DimensionScores(
            volume=self._volume_dimension(data.complaint_count),
            severity=self._severity_dimension(data.avg_severity, data.max_severity),
            market_indicators=self._market_indicators_dimension(data),
            implementation_ease=self._implementation_ease_dimension(
                data.category_code,
                data.domain_code,
            ),
            founder_fit=self._founder_fit_dimension(
                data.domain_code,
                data.dominant_persona_code,
                data.category_code,
            ),
        )

        weighted = (
            self._weights["volume"] * dimensions.volume
            + self._weights["severity"] * dimensions.severity
            + self._weights["market_indicators"] * dimensions.market_indicators
            + self._weights["implementation_ease"] * dimensions.implementation_ease
            + self._weights["founder_fit"] * dimensions.founder_fit
        )
        score = int(round(min(100.0, max(0.0, weighted))))

        volume_score = dimensions.volume / 100
        severity_score = dimensions.severity / 100
        market_indicator_score = dimensions.market_indicators / 100
        implementation_ease_score = dimensions.implementation_ease / 100
        founder_fit_score = dimensions.founder_fit / 100
        overall_score = round(score / 100, 4)

        explanation = (
            f"Score {score}/100 from {data.complaint_count} complaints "
            f"(avg severity {data.avg_severity:.1f}/5). "
            f"Volume={dimensions.volume}, severity={dimensions.severity}, "
            f"market indicators={dimensions.market_indicators}, "
            f"implementation ease={dimensions.implementation_ease}, "
            f"founder fit={dimensions.founder_fit}. "
            "Market indicators use complaint evidence only (no external research)."
        )

        return ScoringResult(
            score=score,
            dimensions=dimensions,
            volume_score=volume_score,
            severity_score=severity_score,
            market_indicator_score=market_indicator_score,
            implementation_ease_score=implementation_ease_score,
            founder_fit_score=founder_fit_score,
            overall_score=overall_score,
            confidence_score=data.confidence_score,
            explanation=explanation,
        )

    def _volume_dimension(self, complaint_count: int) -> int:
        if complaint_count <= 0:
            return 0
        ratio = min(1.0, complaint_count / self._volume_target)
        return int(round(ratio * 100))

    def _severity_dimension(self, avg_severity: float, max_severity: int) -> int:
        avg_component = (avg_severity / 5) * 70
        max_component = (max_severity / 5) * 30
        return int(round(min(100.0, avg_component + max_component)))

    def _market_indicators_dimension(self, data: ScoringInput) -> int:
        """Evidence-only market signal: alternatives mentioned, product diversity, confidence."""
        product_signal = min(1.0, data.unique_product_count / 5) * 35
        volume_signal = min(1.0, data.complaint_count / 20) * 30
        alternatives_signal = 20 if data.has_documented_alternatives else 5
        gap_signal = 15 if len(data.gap_text.strip()) >= 30 else 5
        confidence_signal = data.confidence_score * 20
        total = (
            product_signal
            + volume_signal
            + alternatives_signal
            + gap_signal
            + confidence_signal
        )
        return int(round(min(100.0, total)))

    def _implementation_ease_dimension(self, category_code: str, domain_code: str) -> int:
        category_ease = CATEGORY_IMPLEMENTATION_EASE.get(category_code, 0.55)
        domain_ease = DOMAIN_IMPLEMENTATION_EASE.get(domain_code, 0.50)
        combined = (category_ease * 0.6) + (domain_ease * 0.4)
        return int(round(combined * 100))

    def _founder_fit_dimension(
        self,
        domain_code: str,
        persona_code: str,
        category_code: str,
    ) -> int:
        domain_fit = FOUNDER_FIT_DOMAIN.get(domain_code, 0.50)
        persona_fit = 0.85 if persona_code in FOUNDER_FIT_PERSONAS else 0.55
        category_penalty = 0.10 if category_code in {"security", "integration"} else 0.0
        combined = (domain_fit * 0.55) + (persona_fit * 0.45) - category_penalty
        return int(round(min(100.0, max(0.0, combined * 100))))
