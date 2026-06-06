"""Tests for Security mechanism fingerprint extraction and formation replay."""

from uuid import uuid4

from app.agents.opportunity.mechanism_fingerprints import (
    enrich_complaint_evidence,
    evaluate_singleton_exception,
    extract_mechanism_fingerprint,
)
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.venture_aware_clustering import detect_venture_aware_patterns

# Security benchmark run f2ed171c — classified complaint evidence.
SECURITY_BENCHMARK_CORPUS: list[dict] = [
    {
        "title": "Ask HN: Found security vulnerability at work. rebuked. was I wrong?",
        "summary": (
            "The user feels they were unfairly reprimanded for identifying a security "
            "vulnerability in their company's test environment and believes they acted "
            "responsibly by reporting it."
        ),
        "verbatim_quote": (
            "Instead I was told that I risked termination and I should tell someone first."
        ),
        "severity": 3,
        "business_function_code": "fraud_prevention",
        "jtbd_code": "prevent_fraud",
        "consequence_code": "operational_risk",
    },
    {
        "title": "Ask HN: Security vulnerability in deployment – what to do?",
        "summary": (
            "The user has identified a critical security vulnerability in a deployed web "
            "page and is seeking guidance on how to address the lack of response from the "
            "person responsible for the deployment."
        ),
        "verbatim_quote": (
            "I found a security vulnerability in a web page I developed, which was "
            "deployed by another person: A GET to an easily-guessable URL gives away a "
            "file containing a password with which one can login and modify content."
        ),
        "severity": 5,
        "business_function_code": "deployment",
        "jtbd_code": "prevent_fraud",
        "consequence_code": "operational_risk",
    },
    {
        "title": "Ask HN: Altrec security breach letter?",
        "summary": (
            "The user expresses concern over a potential security breach involving their "
            "personal information and questions the legitimacy of the communication from "
            "Altrec regarding the incident."
        ),
        "verbatim_quote": "Is this on the level?",
        "severity": 4,
        "business_function_code": "fraud_prevention",
        "jtbd_code": "prevent_fraud",
        "consequence_code": "customer_loss",
    },
    {
        "title": "Ask HN: Security negligence by former employer, a health insurance co.?",
        "summary": (
            "The user expresses concern over severe data security negligence by a former "
            "employer, a health insurance company, following a ransomware attack that "
            "compromised sensitive personal data of millions."
        ),
        "verbatim_quote": (
            "This situation seems to reflect severe negligence, if not intentional disregard."
        ),
        "severity": 5,
        "business_function_code": "fraud_prevention",
        "jtbd_code": "prevent_fraud",
        "consequence_code": "customer_loss",
    },
    {
        "title": "Ask HN: Security vulnerability discovered during interview",
        "summary": (
            "The user discovered a potential security vulnerability during an interview, "
            "specifically a session fixation issue that could lead to data breaches."
        ),
        "verbatim_quote": (
            "I noticed what appeared to be a session fixation vulnerability where - and "
            "I kid you not - the session ID is the user's email."
        ),
        "severity": 4,
        "business_function_code": "fraud_prevention",
        "jtbd_code": "prevent_fraud",
        "consequence_code": "operational_risk",
    },
]

# Prior cross-corpus corpus — retains unpatched-vuln follow-up phrasing.
UNPATCHED_VULN_COMPLAINT = {
    "summary": (
        "The user is facing a critical security vulnerability that has not been "
        "addressed despite multiple follow-ups."
    ),
    "verbatim_quote": (
        "I reported that vulnerability immediately to the person deploying it and "
        "he answered he would look into it and reply. He did not."
    ),
}


def _security_evidence(row: dict) -> ComplaintEvidence:
    return ComplaintEvidence(
        id=uuid4(),
        summary=row["summary"],
        verbatim_quote=row["verbatim_quote"],
        severity=row["severity"],
        domain_code="saas_b2b",
        category_code="security",
        persona_code="developer",
        business_function_code=row["business_function_code"],
        jtbd_code=row["jtbd_code"],
        consequence_code=row["consequence_code"],
    )


def _benchmark_corpus_evidence() -> list[ComplaintEvidence]:
    return [_security_evidence(row) for row in SECURITY_BENCHMARK_CORPUS]


def test_extracts_vulnerability_disclosure_workflow() -> None:
    row = SECURITY_BENCHMARK_CORPUS[0]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "vulnerability_disclosure_workflow"
    )


def test_extracts_endpoint_security_negligence_deployment_vuln() -> None:
    row = SECURITY_BENCHMARK_CORPUS[1]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "endpoint_security_negligence"
    )


def test_extracts_endpoint_security_negligence_unpatched_followup() -> None:
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=UNPATCHED_VULN_COMPLAINT["verbatim_quote"],
            summary=UNPATCHED_VULN_COMPLAINT["summary"],
        )
        == "endpoint_security_negligence"
    )


def test_extracts_incident_response_coordination() -> None:
    row = SECURITY_BENCHMARK_CORPUS[3]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "incident_response_coordination"
    )


def test_extracts_session_fixation_exposure() -> None:
    row = SECURITY_BENCHMARK_CORPUS[4]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "session_fixation_exposure"
    )


def test_thin_phishing_quote_does_not_match_security_fingerprint() -> None:
    row = SECURITY_BENCHMARK_CORPUS[2]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        is None
    )
    member = enrich_complaint_evidence(_security_evidence(row))
    assert evaluate_singleton_exception(member) is None


def test_generic_security_keyword_does_not_match() -> None:
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote="We need better security for our app.",
            summary="General security improvement request.",
        )
        is None
    )


def test_generic_breach_and_hack_do_not_match() -> None:
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote="There was a breach at our company last week.",
            summary="Security breach concern.",
        )
        is None
    )
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote="Someone might hack our servers.",
            summary="Hack prevention question.",
        )
        is None
    )


def test_stripe_fingerprint_unchanged_after_security_rules() -> None:
    quote = "I just got kicked off Stripe; classified as high risk."
    assert extract_mechanism_fingerprint(verbatim_quote=quote) == (
        "processor_account_deplatforming"
    )


def test_security_benchmark_v11_venture_aware_replay() -> None:
    evidence = [enrich_complaint_evidence(item) for item in _benchmark_corpus_evidence()]

    outcomes = []
    for row, member in zip(SECURITY_BENCHMARK_CORPUS, evidence, strict=True):
        singleton = evaluate_singleton_exception(member)
        outcomes.append(
            {
                "title": row["title"],
                "mechanism_fingerprint": member.mechanism_fingerprint,
                "singleton_exception": singleton is not None,
            }
        )

    patterns = detect_venture_aware_patterns(evidence, emit_logs=False)

    assert outcomes == [
        {
            "title": "Ask HN: Found security vulnerability at work. rebuked. was I wrong?",
            "mechanism_fingerprint": "vulnerability_disclosure_workflow",
            "singleton_exception": True,
        },
        {
            "title": "Ask HN: Security vulnerability in deployment – what to do?",
            "mechanism_fingerprint": "endpoint_security_negligence",
            "singleton_exception": True,
        },
        {
            "title": "Ask HN: Altrec security breach letter?",
            "mechanism_fingerprint": None,
            "singleton_exception": False,
        },
        {
            "title": "Ask HN: Security negligence by former employer, a health insurance co.?",
            "mechanism_fingerprint": "incident_response_coordination",
            "singleton_exception": True,
        },
        {
            "title": "Ask HN: Security vulnerability discovered during interview",
            "mechanism_fingerprint": "session_fixation_exposure",
            "singleton_exception": True,
        },
    ]
    assert len(patterns) == 4
    assert {p.mechanism_fingerprint for p in patterns} == {
        "vulnerability_disclosure_workflow",
        "endpoint_security_negligence",
        "incident_response_coordination",
        "session_fixation_exposure",
    }
    assert all(p.singleton_exception_reason for p in patterns)
