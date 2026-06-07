"""Tests for mechanism-primary topic generation."""

from app.agents.opportunity.founder_signal_clustering import derive_coherent_topic
from app.agents.opportunity.mechanism_topics import format_mechanism_primary_topic
from app.agents.opportunity.schemas import ComplaintEvidence
from uuid import uuid4


def _member(**overrides) -> ComplaintEvidence:
    payload = {
        "id": uuid4(),
        "summary": "Summary text.",
        "verbatim_quote": "Representative quote for topic generation.",
        "severity": 4,
        "domain_code": "devtools",
        "category_code": "performance",
        "persona_code": "developer",
    }
    payload.update(overrides)
    return ComplaintEvidence(**payload)


def test_mechanism_primary_topic_for_mcp() -> None:
    topic = format_mechanism_primary_topic("mcp_discovery_overhead", "operational_overhead")
    assert topic == "Agent Tooling — Configure Agent Tools — Operational Overhead"


def test_mechanism_primary_topic_for_gpu_compute() -> None:
    topic = format_mechanism_primary_topic(
        "gpu_compute_access_unreliability",
        "operational_risk",
        verbatim_quote="renting GPUs from vast.ai is unreliable",
    )
    assert topic == "Gpu Compute — Provision Compute — Operational Risk"


def test_derive_coherent_topic_uses_mechanism_fallback_when_incoherent() -> None:
    topic = derive_coherent_topic(
        cluster_key="payment_processor|accept_payments|revenue_interruption|gpu_compute_access_unreliability",
        business_function_code="payment_processor",
        jtbd_code="accept_payments",
        consequence_code="revenue_interruption",
        members=[_member(verbatim_quote="renting GPUs is unreliable on vast.ai")],
        mechanism_fingerprint="gpu_compute_access_unreliability",
    )
    assert topic == "Gpu Compute — Provision Compute — Revenue Interruption"


def test_derive_coherent_topic_uses_signal_labels_when_coherent() -> None:
    topic = derive_coherent_topic(
        cluster_key="agent_tooling|configure_agent_tools|operational_overhead|mcp_discovery_overhead",
        business_function_code="agent_tooling",
        jtbd_code="configure_agent_tools",
        consequence_code="operational_overhead",
        members=[_member()],
        mechanism_fingerprint="mcp_discovery_overhead",
    )
    assert topic == "Agent Tooling — Configure Agent Tools — Operational Overhead"
