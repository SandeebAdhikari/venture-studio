"""Tests for DevTools V1 mechanism fingerprint extraction and formation replay."""

from uuid import uuid4

from app.agents.opportunity.mechanism_fingerprints import (
    enrich_complaint_evidence,
    evaluate_singleton_exception,
    extract_mechanism_fingerprint,
)
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.venture_aware_clustering import detect_venture_aware_patterns

# DevTools benchmark run c5f3cfd0 — classified complaint evidence.
DEVTOOLS_BENCHMARK_CORPUS: list[dict] = [
    {
        "title": "Ask HN: What am I doing wrong Re Agentic coding",
        "summary": (
            "The user is frustrated with the code generation process, as the tool frequently "
            "deviates from the specified task, leading to wasted time and a lack of trust in "
            "the generated code."
        ),
        "verbatim_quote": (
            "I ended up reverting all the changes as I had absolutely 0 trust in the quality "
            "of the generated code."
        ),
        "severity": 4,
        "domain_code": "devtools",
        "category_code": "performance",
        "persona_code": "developer",
        "business_function_code": "ci_cd",
        "jtbd_code": "deploy_software",
        "consequence_code": "operational_risk",
        "expected_fingerprint": "agentic_code_trust_gap",
    },
    {
        "title": "Ask HN: Front End Developer Burnout",
        "summary": (
            "The user expresses feelings of burnout and frustration due to inconsistent "
            "workflows and constant issues in their role as a front end developer."
        ),
        "verbatim_quote": (
            "I feel the demands on me have gradually become unreasonable over the years."
        ),
        "severity": 4,
        "domain_code": "devtools",
        "category_code": "workflow",
        "persona_code": "developer",
        "business_function_code": "ci_cd",
        "jtbd_code": "deploy_software",
        "consequence_code": "operational_risk",
        "expected_fingerprint": None,
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
        "business_function_code": "agent_tooling",
        "jtbd_code": "configure_agent_tools",
        "consequence_code": "operational_overhead",
        "expected_fingerprint": "mcp_discovery_overhead",
    },
    {
        "title": "Ask HN: Which CI/CD do you use for a monorepo?",
        "summary": (
            "The user is frustrated with the complexity of existing CI/CD tools, particularly "
            "the reliance on YAML configurations, and is seeking a simpler solution."
        ),
        "verbatim_quote": "I am just getting tired of these.",
        "severity": 4,
        "domain_code": "devtools",
        "category_code": "workflow",
        "persona_code": "developer",
        "business_function_code": "ci_cd",
        "jtbd_code": "deploy_software",
        "consequence_code": "operational_overhead",
        "expected_fingerprint": "cicd_yaml_complexity",
    },
    {
        "title": "Ask HN: Templated Build Pipelines for CI/CD. Good or Bad?",
        "summary": (
            "The standardization of deployment processes using templates is causing pushback "
            "from developers who feel restricted by the lack of freedom in the CI/CD system."
        ),
        "verbatim_quote": (
            "The drawback is, of course, lack of freedom for the developers and we are getting "
            "some pushback because of it."
        ),
        "severity": 3,
        "domain_code": "devtools",
        "category_code": "workflow",
        "persona_code": "developer",
        "business_function_code": "ci_cd",
        "jtbd_code": "deploy_software",
        "consequence_code": "operational_risk",
        "expected_fingerprint": "pipeline_template_rigidity",
    },
    {
        "title": "Ask HN: How do I stop getting assigned CI/CD/ops work?",
        "summary": (
            "The user expresses frustration about being assigned CI/CD and operations work "
            "instead of development tasks, indicating a desire for a more fulfilling role."
        ),
        "verbatim_quote": "I'm pretty frustrated by this.",
        "severity": 3,
        "domain_code": "devtools",
        "category_code": "other",
        "persona_code": "developer",
        "business_function_code": "ci_cd",
        "jtbd_code": "deploy_software",
        "consequence_code": "operational_risk",
        "expected_fingerprint": None,
    },
    {
        "title": "Ask HN: A better setup for local Rails dev (Vagrant?)",
        "summary": (
            "The user is experiencing slow load times when using Vagrant for local Rails "
            "development, which is impacting their workflow."
        ),
        "verbatim_quote": (
            "loading a page in the Rails app from the host machine is just too damn slow..."
            "it takes anywhere from 5 to 10+ seconds to refresh the page."
        ),
        "severity": 4,
        "domain_code": "devtools",
        "category_code": "performance",
        "persona_code": "developer",
        "business_function_code": "ci_cd",
        "jtbd_code": "deploy_software",
        "consequence_code": "engineering_friction",
        "expected_fingerprint": "local_dev_performance",
    },
    {
        "title": "Ask HN: Does anybody find schema first design difficult with Open API Spec?",
        "summary": (
            "The user expresses frustration with the tediousness of writing Open API specs and "
            "the inconsistencies in code generation tools, which complicate the development "
            "process."
        ),
        "verbatim_quote": (
            "writing the Open API Spec in yaml is tedious. I find myself having to read the "
            "Open API documentation constantly while writing the spec."
        ),
        "severity": 3,
        "domain_code": "devtools",
        "category_code": "workflow",
        "persona_code": "developer",
        "business_function_code": "ci_cd",
        "jtbd_code": "deploy_software",
        "consequence_code": "engineering_friction",
        "expected_fingerprint": "openapi_spec_friction",
    },
    {
        "title": "Ask HN: Can someone at HubSpot explain some of their API design choices?",
        "summary": (
            "The user expresses frustration with HubSpot's API design and developer experience, "
            "highlighting several specific issues with API support and limitations."
        ),
        "verbatim_quote": (
            "Has anyone else built integrations for hubspot and just been completely fed up "
            "with their terrible developer experience compared to other sales tools?"
        ),
        "severity": 4,
        "domain_code": "saas_b2b",
        "category_code": "integration",
        "persona_code": "developer",
        "business_function_code": "observability",
        "jtbd_code": "deploy_software",
        "consequence_code": "engineering_friction",
        "expected_fingerprint": "platform_api_dx_friction",
    },
]


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


def _corpus_evidence() -> list[ComplaintEvidence]:
    return [_evidence(row) for row in DEVTOOLS_BENCHMARK_CORPUS]


def test_extracts_agentic_code_trust_gap() -> None:
    row = DEVTOOLS_BENCHMARK_CORPUS[0]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "agentic_code_trust_gap"
    )


def test_extracts_mcp_discovery_overhead() -> None:
    row = DEVTOOLS_BENCHMARK_CORPUS[2]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "mcp_discovery_overhead"
    )


def test_extracts_cicd_yaml_complexity_from_summary() -> None:
    row = DEVTOOLS_BENCHMARK_CORPUS[3]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "cicd_yaml_complexity"
    )


def test_extracts_pipeline_template_rigidity() -> None:
    row = DEVTOOLS_BENCHMARK_CORPUS[4]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "pipeline_template_rigidity"
    )


def test_extracts_local_dev_performance() -> None:
    row = DEVTOOLS_BENCHMARK_CORPUS[6]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "local_dev_performance"
    )


def test_extracts_openapi_spec_friction() -> None:
    row = DEVTOOLS_BENCHMARK_CORPUS[7]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "openapi_spec_friction"
    )


def test_extracts_platform_api_dx_friction() -> None:
    row = DEVTOOLS_BENCHMARK_CORPUS[8]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "platform_api_dx_friction"
    )


def test_generic_ci_cd_does_not_match() -> None:
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote="We use CI/CD for deployments.",
            summary="General CI/CD discussion.",
        )
        is None
    )


def test_generic_developer_experience_does_not_match() -> None:
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote="Developer experience matters for adoption.",
            summary="General DX advice.",
        )
        is None
    )


def test_stripe_fingerprint_unchanged() -> None:
    assert (
        extract_mechanism_fingerprint(verbatim_quote="I just got kicked off Stripe; classified as high risk.")
        == "processor_account_deplatforming"
    )


def test_security_fingerprint_unchanged() -> None:
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote="I found a security vulnerability in a web page I developed, which was deployed by another person: A GET to an easily-guessable URL gives away a file containing a password.",
        )
        == "endpoint_security_negligence"
    )


def test_devtools_benchmark_corpus_fingerprint_expectations() -> None:
    for row in DEVTOOLS_BENCHMARK_CORPUS:
        assert (
            extract_mechanism_fingerprint(
                verbatim_quote=row["verbatim_quote"],
                summary=row["summary"],
            )
            == row["expected_fingerprint"]
        )


def test_devtools_benchmark_v1_venture_aware_replay() -> None:
    evidence = [enrich_complaint_evidence(item) for item in _corpus_evidence()]

    outcomes = []
    for row, member in zip(DEVTOOLS_BENCHMARK_CORPUS, evidence, strict=True):
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

    assert len([o for o in outcomes if o["mechanism_fingerprint"]]) == 7
    assert len(patterns) == 7
    assert len(founder_grade) == 7
    assert {p.mechanism_fingerprint for p in patterns} == {
        "agentic_code_trust_gap",
        "mcp_discovery_overhead",
        "cicd_yaml_complexity",
        "pipeline_template_rigidity",
        "local_dev_performance",
        "openapi_spec_friction",
        "platform_api_dx_friction",
    }
    assert not any(o["singleton_exception"] for o in outcomes if "CI/CD/ops work" in o["title"])
