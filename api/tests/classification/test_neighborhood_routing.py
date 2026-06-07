"""Tests for founder signal neighborhood resolution."""

import pytest

from app.agents.classification.neighborhood import (
    FounderSignalNeighborhood,
    normalize_neighborhood,
    resolve_neighborhood,
)
from app.config import Settings
from app.schemas.pipeline import PipelineRunOptions


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("stripe_billing", FounderSignalNeighborhood.STRIPE_BILLING),
        ("stripe", FounderSignalNeighborhood.STRIPE_BILLING),
        ("security", FounderSignalNeighborhood.SECURITY),
        ("devtools_v1", FounderSignalNeighborhood.DEVTOOLS),
        ("ai-infrastructure-v1", FounderSignalNeighborhood.AI_INFRASTRUCTURE),
        ("", None),
        (None, None),
    ],
)
def test_normalize_neighborhood_aliases(raw: str | None, expected: FounderSignalNeighborhood | None) -> None:
    assert normalize_neighborhood(raw) == expected


def test_resolve_neighborhood_defaults_to_stripe() -> None:
    assert resolve_neighborhood() == FounderSignalNeighborhood.STRIPE_BILLING


def test_resolve_neighborhood_prefers_explicit_over_pipeline() -> None:
    opts = PipelineRunOptions(founder_signal_neighborhood="security")
    assert (
        resolve_neighborhood(
            explicit="devtools",
            pipeline_options=opts,
        )
        == FounderSignalNeighborhood.DEVTOOLS
    )


def test_resolve_neighborhood_uses_pipeline_options() -> None:
    opts = PipelineRunOptions(founder_signal_neighborhood="ai_infrastructure")
    assert (
        resolve_neighborhood(pipeline_options=opts)
        == FounderSignalNeighborhood.AI_INFRASTRUCTURE
    )


def test_resolve_neighborhood_uses_settings() -> None:
    settings = Settings(api_key="x" * 16, founder_signal_neighborhood="security")
    assert resolve_neighborhood(settings=settings) == FounderSignalNeighborhood.SECURITY
