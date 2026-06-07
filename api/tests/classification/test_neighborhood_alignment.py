"""Tests for per-neighborhood alignment prompt routing."""

from app.agents.classification.neighborhood import FounderSignalNeighborhood
from app.agents.classification.problem_category_alignment import (
    alignment_prompt_block,
    alignment_prompt_for_neighborhood,
)


def test_stripe_alignment_preserves_namespace_guidance() -> None:
    block = alignment_prompt_for_neighborhood(FounderSignalNeighborhood.STRIPE_BILLING)
    assert "problem_category must NEVER be 'billing'" in block
    assert "Kicked off Stripe" in block


def test_security_alignment_includes_negative_examples() -> None:
    block = alignment_prompt_for_neighborhood(FounderSignalNeighborhood.SECURITY)
    assert "NEGATIVE examples" in block
    assert "fraud_prevention" in block
    assert "vulnerability_management" in block


def test_ai_infrastructure_alignment_includes_negative_examples() -> None:
    block = alignment_prompt_for_neighborhood(FounderSignalNeighborhood.AI_INFRASTRUCTURE)
    assert "NEGATIVE examples" in block
    assert "payment_processor" in block
    assert "agent_tooling" in block


def test_alignment_prompt_block_defaults_to_stripe() -> None:
    block = alignment_prompt_block()
    stripe = alignment_prompt_for_neighborhood(FounderSignalNeighborhood.STRIPE_BILLING)
    assert "Stripe billing fees" in block
    assert block == stripe


def test_alignment_prompt_block_routes_by_neighborhood() -> None:
    security = alignment_prompt_block(FounderSignalNeighborhood.SECURITY)
    devtools = alignment_prompt_block("devtools")
    assert "remediate_vulnerabilities" in security
    assert "configure_agent_tools" in devtools
