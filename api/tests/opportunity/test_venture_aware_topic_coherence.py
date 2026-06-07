"""Venture-aware topic coherence after PR-2 overlays."""

from uuid import uuid4

from app.agents.classification.signal_overlays import enrich_complaint_evidence_with_overlay
from app.agents.opportunity.venture_aware_clustering import detect_venture_aware_patterns
from app.agents.opportunity.schemas import ComplaintEvidence
from tests.opportunity.test_ai_infrastructure_mechanism_fingerprints import (
    AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS,
)
from tests.opportunity.test_devtools_mechanism_fingerprints import DEVTOOLS_BENCHMARK_CORPUS
from tests.opportunity.test_security_mechanism_fingerprints import SECURITY_BENCHMARK_CORPUS


def _corpus_evidence(rows: list[dict]) -> list[ComplaintEvidence]:
    evidence = []
    for row in rows:
        evidence.append(
            ComplaintEvidence(
                id=uuid4(),
                summary=row["summary"],
                verbatim_quote=row["verbatim_quote"],
                severity=row["severity"],
                domain_code=row.get("domain_code", "saas_b2b"),
                category_code=row.get("category_code", "security"),
                persona_code=row.get("persona_code", "developer"),
                business_function_code=row["business_function_code"],
                jtbd_code=row["jtbd_code"],
                consequence_code=row["consequence_code"],
            )
        )
    return evidence


def test_security_topics_use_native_security_labels() -> None:
    # Simulate legacy fintech leakage still present in DB complaints.
    leaked = []
    for row in SECURITY_BENCHMARK_CORPUS:
        copy = dict(row)
        copy["business_function_code"] = "fraud_prevention"
        copy["jtbd_code"] = "prevent_fraud"
        leaked.append(copy)

    evidence = [
        enrich_complaint_evidence_with_overlay(item) for item in _corpus_evidence(leaked)
    ]
    patterns = detect_venture_aware_patterns(evidence, emit_logs=False)
    topics = {p.mechanism_fingerprint: p.topic for p in patterns}

    assert topics["vulnerability_disclosure_workflow"].startswith("Vulnerability Management")
    assert topics["incident_response_coordination"].startswith("Incident Response")
    assert topics["session_fixation_exposure"].startswith("Application Security")


def test_devtools_mcp_topic_is_agent_tooling() -> None:
    leaked = []
    for row in DEVTOOLS_BENCHMARK_CORPUS:
        copy = dict(row)
        if row.get("expected_fingerprint") == "mcp_discovery_overhead":
            copy["business_function_code"] = "observability"
            copy["jtbd_code"] = "manage_subscriptions"
        leaked.append(copy)

    evidence = [
        enrich_complaint_evidence_with_overlay(item) for item in _corpus_evidence(leaked)
    ]
    patterns = detect_venture_aware_patterns(evidence, emit_logs=False)
    mcp = next(p for p in patterns if p.mechanism_fingerprint == "mcp_discovery_overhead")
    assert mcp.topic.startswith("Agent Tooling — Configure Agent Tools")


def test_ai_infrastructure_topics_match_v2_families() -> None:
    leaked = []
    for row in AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS:
        copy = dict(row)
        fp = row.get("expected_fingerprint")
        if fp == "gpu_compute_access_unreliability" and "Vast.ai" in row["title"]:
            copy["business_function_code"] = "payment_processor"
            copy["jtbd_code"] = "accept_payments"
        elif fp == "inference_cost_governance":
            copy["business_function_code"] = "billing_operations"
            copy["jtbd_code"] = "manage_subscriptions"
        elif fp == "ai_eval_pipeline_gap":
            copy["business_function_code"] = "observability"
            copy["jtbd_code"] = "monitor_systems"
        leaked.append(copy)

    evidence = [
        enrich_complaint_evidence_with_overlay(item) for item in _corpus_evidence(leaked)
    ]
    patterns = detect_venture_aware_patterns(evidence, emit_logs=False)
    gpu_topics = [
        p.topic for p in patterns if p.mechanism_fingerprint == "gpu_compute_access_unreliability"
    ]
    assert any(topic.startswith("Gpu Compute") for topic in gpu_topics)
    assert any(topic.startswith("Capacity Management") for topic in gpu_topics)

    topics = {p.mechanism_fingerprint: p.topic for p in patterns}
    assert topics["inference_cost_governance"].startswith("Inference Governance")
    assert topics["ai_eval_pipeline_gap"].startswith("Llm Evaluation")
