"""Tests for AI Infrastructure V1 mechanism fingerprint extraction and formation replay."""

from uuid import uuid4

from app.agents.opportunity.mechanism_fingerprints import (
    enrich_complaint_evidence,
    evaluate_singleton_exception,
    extract_mechanism_fingerprint,
)
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.venture_aware_clustering import detect_venture_aware_patterns

# Locked AI Infrastructure query set — venture-worthy complaints (audit 2026-06-06).
AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS: list[dict] = [
    {
        "title": "Ask HN: What's the Deal with Vast.ai?",
        "summary": (
            "The user expresses frustration with the reliability and performance of vast.ai's "
            "GPU rental service, noting discrepancies between reported and actual performance metrics."
        ),
        "verbatim_quote": (
            "As a client (renting GPUs) I've found it to be pretty unreliable. I've tried "
            "renting GPUs a handful of times and hosts, bandwidth, and performance are all over "
            "the place compared to what's listed in the console."
        ),
        "severity": 4,
        "domain_code": "devtools",
        "category_code": "performance",
        "persona_code": "developer",
        "business_function_code": "payment_processor",
        "jtbd_code": "accept_payments",
        "consequence_code": "revenue_interruption",
        "expected_fingerprint": "gpu_compute_access_unreliability",
        "expected_singleton": True,
    },
    {
        "title": "Ask HN: What tools are you using for AI evals? Everything feels half-baked",
        "summary": (
            "The user is struggling to find effective tools for evaluating LLMs in production "
            "due to significant limitations in existing solutions."
        ),
        "verbatim_quote": (
            "Been trying to build a proper evaluation pipeline for months but every tool we've "
            "tested has significant limitations."
        ),
        "severity": 4,
        "domain_code": "devtools",
        "category_code": "missing_feature",
        "persona_code": "developer",
        "business_function_code": "observability",
        "jtbd_code": "monitor_systems",
        "consequence_code": "operational_overhead",
        "expected_fingerprint": "ai_eval_pipeline_gap",
        "expected_singleton": True,
    },
    {
        "title": "Ask HN: Are we forcing LLMs to be State Machines?",
        "summary": (
            "The user expresses frustration with the challenges of integrating AI agents into "
            "customer service workflows, highlighting the difficulty in managing user intent."
        ),
        "verbatim_quote": (
            "It feels like I spend 80% of my engineering effort building guardrails to "
            "prevent hallucinations or catastrophic logic failures, and only 20% actually "
            "shipping features."
        ),
        "severity": 4,
        "domain_code": "saas_b2b",
        "category_code": "performance",
        "persona_code": "developer",
        "business_function_code": "deployment",
        "jtbd_code": "deploy_software",
        "consequence_code": "operational_risk",
        "expected_fingerprint": "llm_guardrail_engineering_tax",
        "expected_singleton": True,
    },
    {
        "title": "Ask HN: Is manually discovering and configuring MCP servers the only way?",
        "summary": (
            "The user expresses frustration with the time-consuming process of discovering "
            "and configuring MCP servers for their agent, seeking a more efficient solution."
        ),
        "verbatim_quote": 'This feels incredibly time-consuming and not "agentic".',
        "severity": 4,
        "domain_code": "devtools",
        "category_code": "workflow",
        "persona_code": "developer",
        "business_function_code": "observability",
        "jtbd_code": "manage_subscriptions",
        "consequence_code": "operational_overhead",
        "expected_fingerprint": "mcp_discovery_overhead",
        "expected_singleton": True,
    },
    {
        "title": "Ask HN: Google Colab alternatives for large lang models?",
        "summary": (
            "The user is experiencing significant frustration with Google Colab's GPU availability "
            "and quota denials, which is hindering their ability to run LLM experiments efficiently."
        ),
        "verbatim_quote": (
            "But I'm finding that most of the paid Google Colab options don't work. Instead of "
            "working on the LLM experiments, I'm wasting considerable time on infrastructure."
        ),
        "severity": 4,
        "domain_code": "other",
        "category_code": "performance",
        "persona_code": "developer",
        "business_function_code": "observability",
        "jtbd_code": "deploy_software",
        "consequence_code": "operational_overhead",
        "expected_fingerprint": "gpu_compute_access_unreliability",
        "expected_singleton": True,
    },
    {
        "title": "Ask HN: Coding agents struggle to get the current OpenAI API Spec?",
        "summary": (
            "The user expresses frustration over the difficulty in accessing the official "
            "OpenAI API specification, indicating a need for better tools to facilitate this process."
        ),
        "verbatim_quote": (
            "This is a basic task that should not be this broken. I think there is clear need "
            "and opportunity for better tooling here or is it a skill issue?"
        ),
        "severity": 4,
        "domain_code": "devtools",
        "category_code": "missing_feature",
        "persona_code": "developer",
        "business_function_code": "observability",
        "jtbd_code": "monitor_systems",
        "consequence_code": "operational_risk",
        "expected_fingerprint": "coding_agent_api_spec_gap",
        "expected_singleton": True,
    },
    {
        "title": "Ask HN: Company is rapidly cutting AI tool spend how to prep team?",
        "summary": (
            "The user expresses concern over the company's decision to cut AI tool spending, "
            "particularly the removal of Claude access, which is impacting workflows and productivity."
        ),
        "verbatim_quote": (
            "Reasoning is cost apparently our monthly Claude bill has become astronomical for the "
            "org. Nearly 3x our saas's cloud spend."
        ),
        "severity": 4,
        "domain_code": "saas_b2b",
        "category_code": "pricing",
        "persona_code": "developer",
        "business_function_code": "billing_operations",
        "jtbd_code": "manage_subscriptions",
        "consequence_code": "operational_overhead",
        "expected_fingerprint": "inference_cost_governance",
        "expected_singleton": True,
    },
    {
        "title": "Ask HN: MCP calls leading to dynamic context length issues",
        "summary": (
            "The user is experiencing issues with MCP calls that lead to exceeding input context "
            "length limits in their agentic builder."
        ),
        "verbatim_quote": (
            "some mcp sources can give a huge output which can cross the input context length limit."
        ),
        "severity": 3,
        "domain_code": "devtools",
        "category_code": "performance",
        "persona_code": "developer",
        "business_function_code": "observability",
        "jtbd_code": "monitor_systems",
        "consequence_code": "operational_risk",
        "expected_fingerprint": "mcp_context_budget_overflow",
        "expected_singleton": True,
    },
    {
        "title": "Ask HN: Playwright MCP Unusable?",
        "summary": (
            "The user is experiencing issues with the Playwright MCP causing frequent context "
            "window failures during browser automation."
        ),
        "verbatim_quote": "it constantly blows up the context window on nearly every call.",
        "severity": 3,
        "domain_code": "devtools",
        "category_code": "performance",
        "persona_code": "developer",
        "business_function_code": "observability",
        "jtbd_code": "deploy_software",
        "consequence_code": "operational_risk",
        "expected_fingerprint": "mcp_context_budget_overflow",
        "expected_singleton": True,
    },
    {
        "title": "Ask HN: Is there a free MCP for web and documentation search?",
        "summary": (
            "The user is looking for a free solution for web and documentation search that can "
            "handle JS-only sites and is frustrated with existing options that either cost money "
            "or have limitations."
        ),
        "verbatim_quote": (
            "I'm struggling to find a way for Codex to perform thorough searches without having "
            "to pay for a plan or wasting tokens."
        ),
        "severity": 3,
        "domain_code": "devtools",
        "category_code": "missing_feature",
        "persona_code": "developer",
        "business_function_code": "observability",
        "jtbd_code": "manage_subscriptions",
        "consequence_code": "operational_overhead",
        "expected_fingerprint": None,
        "expected_singleton": False,
    },
    {
        "title": "Ask HN: Gemini Reliability Degrading?",
        "summary": (
            "The user is experiencing slowness and errors with the Gemini web interface, "
            "indicating potential reliability issues."
        ),
        "verbatim_quote": (
            "It's been super reliable until probably the past few days, where I am seeing a lot "
            "of slowness and 'errors', with chats not working or stopping after a few hundred "
            "tokens response."
        ),
        "severity": 3,
        "domain_code": "other",
        "category_code": "performance",
        "persona_code": "developer",
        "business_function_code": "observability",
        "jtbd_code": "monitor_systems",
        "consequence_code": "operational_risk",
        "expected_fingerprint": None,
        "expected_singleton": False,
    },
    {
        "title": "Ask HN: How does your data science or machine learning team handle DevOps?",
        "summary": (
            "The text discusses the challenges faced by data science and machine learning teams "
            "in managing DevOps tasks, which detracts from their core responsibilities and leads "
            "to burnout."
        ),
        "verbatim_quote": (
            "Increasingly teams of data scientists are required to do devops work configuring "
            "and maintaining eg kubernetes & CI/CD workloads, alerting and monitoring, logging, "
            "instrumenting security or data access control compliance solutions."
        ),
        "severity": 4,
        "domain_code": "devtools",
        "category_code": "workflow",
        "persona_code": "developer",
        "business_function_code": "ci_cd",
        "jtbd_code": "deploy_software",
        "consequence_code": "operational_overhead",
        "expected_fingerprint": None,
        "expected_singleton": False,
    },
]

AI_INFRASTRUCTURE_NOISE_CORPUS: list[dict] = [
    {
        "title": "Ask HN: Best Self Hosted Comment System?",
        "summary": (
            "The user is seeking a self-hosted comment system that does not rely on third-party "
            "services due to concerns about costs and dependency on external businesses."
        ),
        "verbatim_quote": (
            "I'm currently using WP Disqus, but it costs a fortune because of their business "
            "model (charging for every extra feature)."
        ),
        "severity": 3,
        "domain_code": "other",
        "category_code": "missing_feature",
        "persona_code": "developer",
        "business_function_code": "subscription_management",
        "jtbd_code": "manage_subscriptions",
        "consequence_code": "operational_overhead",
        "expected_fingerprint": None,
        "expected_singleton": False,
    },
    {
        "title": "Ask HN: Am I a bad person if I give up on Docker Compose?",
        "summary": (
            "The user is frustrated with Docker Compose due to issues with build regressions "
            "and difficulties in managing multiple tools."
        ),
        "verbatim_quote": "I just find myself staring at so many layers of tools.",
        "severity": 3,
        "domain_code": "devtools",
        "category_code": "performance",
        "persona_code": "developer",
        "business_function_code": "deployment",
        "jtbd_code": "deploy_software",
        "consequence_code": "engineering_friction",
        "expected_fingerprint": None,
        "expected_singleton": False,
    },
]

OPENAPI_AUTHORING_QUOTE = (
    "writing the Open API Spec in yaml is tedious. I find myself having to read the "
    "Open API documentation constantly while writing the spec."
)

AI_INFRASTRUCTURE_EXPECTED_FINGERPRINTS = frozenset(
    {
        "mcp_discovery_overhead",
        "coding_agent_api_spec_gap",
        "mcp_context_budget_overflow",
        "llm_guardrail_engineering_tax",
        "ai_eval_pipeline_gap",
        "inference_cost_governance",
        "gpu_compute_access_unreliability",
    }
)


def _evidence(row: dict) -> ComplaintEvidence:
    return ComplaintEvidence(
        id=uuid4(),
        summary=row["summary"],
        verbatim_quote=row["verbatim_quote"],
        severity=row["severity"],
        domain_code=row["domain_code"],
        category_code=row["category_code"],
        persona_code=row["persona_code"],
        business_function_code=row["business_function_code"],
        jtbd_code=row["jtbd_code"],
        consequence_code=row["consequence_code"],
    )


def _venture_worthy_evidence() -> list[ComplaintEvidence]:
    return [_evidence(row) for row in AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS]


def test_extracts_llm_guardrail_engineering_tax() -> None:
    row = AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS[2]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "llm_guardrail_engineering_tax"
    )


def test_extracts_ai_eval_pipeline_gap() -> None:
    row = AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS[1]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "ai_eval_pipeline_gap"
    )


def test_extracts_inference_cost_governance() -> None:
    row = AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS[6]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "inference_cost_governance"
    )


def test_extracts_gpu_compute_access_unreliability_vast_ai() -> None:
    row = AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS[0]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "gpu_compute_access_unreliability"
    )


def test_extracts_gpu_compute_access_unreliability_colab() -> None:
    row = AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS[4]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "gpu_compute_access_unreliability"
    )


def test_extracts_coding_agent_api_spec_gap_from_classified_summary() -> None:
    row = AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS[5]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "coding_agent_api_spec_gap"
    )


def test_extracts_mcp_context_budget_overflow_dynamic_context() -> None:
    row = AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS[7]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "mcp_context_budget_overflow"
    )


def test_extracts_mcp_context_budget_overflow_playwright() -> None:
    row = AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS[8]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "mcp_context_budget_overflow"
    )


def test_guardrail_quote_does_not_match_agentic_code_trust_gap() -> None:
    row = AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS[2]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        != "agentic_code_trust_gap"
    )


def test_disqus_noise_does_not_match() -> None:
    row = AI_INFRASTRUCTURE_NOISE_CORPUS[0]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        is None
    )


def test_docker_compose_noise_does_not_match() -> None:
    row = AI_INFRASTRUCTURE_NOISE_CORPUS[1]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        is None
    )


def test_openapi_authoring_matches_openapi_spec_friction_not_coding_agent() -> None:
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=OPENAPI_AUTHORING_QUOTE,
            summary="OpenAPI schema-first design frustration.",
        )
        == "openapi_spec_friction"
    )
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=OPENAPI_AUTHORING_QUOTE,
            summary="OpenAPI schema-first design frustration.",
        )
        != "coding_agent_api_spec_gap"
    )


def test_stripe_fingerprint_unchanged() -> None:
    assert (
        extract_mechanism_fingerprint(verbatim_quote="I just got kicked off Stripe; classified as high risk.")
        == "processor_account_deplatforming"
    )


def test_security_fingerprint_unchanged() -> None:
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=(
                "I found a security vulnerability in a web page I developed, which was deployed "
                "by another person: A GET to an easily-guessable URL gives away a file containing "
                "a password with which one can login and modify content."
            ),
        )
        == "endpoint_security_negligence"
    )


def test_ai_infrastructure_venture_worthy_corpus_fingerprint_expectations() -> None:
    for row in AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS:
        assert (
            extract_mechanism_fingerprint(
                verbatim_quote=row["verbatim_quote"],
                summary=row["summary"],
            )
            == row["expected_fingerprint"]
        )


def test_ai_infrastructure_v1_venture_aware_replay() -> None:
    evidence = [enrich_complaint_evidence(item) for item in _venture_worthy_evidence()]

    outcomes = []
    for row, member in zip(AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS, evidence, strict=True):
        singleton = evaluate_singleton_exception(member)
        outcomes.append(
            {
                "title": row["title"],
                "mechanism_fingerprint": member.mechanism_fingerprint,
                "singleton_exception": singleton is not None,
            }
        )

    patterns = detect_venture_aware_patterns(evidence, emit_logs=False)
    founder_grade = [o for o in outcomes if o["singleton_exception"]]
    matched = [o for o in outcomes if o["mechanism_fingerprint"]]
    unformed = [o for o in outcomes if not o["singleton_exception"]]

    assert len(matched) == 9
    assert len(patterns) == 9
    assert len(founder_grade) == 9
    assert len(unformed) == 3
    assert {p.mechanism_fingerprint for p in patterns} == AI_INFRASTRUCTURE_EXPECTED_FINGERPRINTS
    assert all(p.singleton_exception_reason for p in patterns)
    assert not any(
        o["singleton_exception"]
        for o in outcomes
        if o["title"] == "Ask HN: Is there a free MCP for web and documentation search?"
    )
    assert not any(
        o["singleton_exception"]
        for o in outcomes
        if o["title"] == "Ask HN: Gemini Reliability Degrading?"
    )
    assert not any(
        o["singleton_exception"]
        for o in outcomes
        if "data science or machine learning team handle DevOps" in o["title"]
    )


def test_state_machines_exclusive_to_ai_infrastructure_corpus() -> None:
    from tests.opportunity.test_devtools_mechanism_fingerprints import DEVTOOLS_BENCHMARK_CORPUS

    devtools_titles = {row["title"] for row in DEVTOOLS_BENCHMARK_CORPUS}
    assert "Ask HN: Are we forcing LLMs to be State Machines?" not in devtools_titles
    assert any(
        row["title"] == "Ask HN: Are we forcing LLMs to be State Machines?"
        for row in AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS
    )


def test_ai_infrastructure_full_locked_corpus_includes_noise_without_extra_patterns() -> None:
    rows = AI_INFRASTRUCTURE_VENTURE_WORTHY_CORPUS + AI_INFRASTRUCTURE_NOISE_CORPUS
    evidence = [enrich_complaint_evidence(_evidence(row)) for row in rows]
    patterns = detect_venture_aware_patterns(evidence, emit_logs=False)
    assert len(patterns) == 9
