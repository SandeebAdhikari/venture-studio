"""Tests for Security mechanism fingerprint extraction and formation replay."""

from uuid import uuid4

from app.agents.opportunity.mechanism_fingerprints import (
    enrich_complaint_evidence,
    evaluate_singleton_exception,
    extract_mechanism_fingerprint,
)
from app.agents.opportunity.schemas import ComplaintEvidence
from app.agents.opportunity.venture_aware_clustering import detect_venture_aware_patterns

# Cross-corpus Security run (b7803eaf) — classified complaint evidence.
SECURITY_CORPUS: list[dict] = [
    {
        "title": "Internal vuln report reprimanded",
        "summary": (
            "The user feels they were unfairly reprimanded for reporting a security "
            "vulnerability they discovered in their company's test environment."
        ),
        "verbatim_quote": (
            "Instead I was told that I risked termination and I should tell someone first."
        ),
        "severity": 4,
        "business_function_code": "fraud_prevention",
        "jtbd_code": "prevent_fraud",
        "consequence_code": "operational_risk",
    },
    {
        "title": "Unpatched vulnerability ignored",
        "summary": (
            "The user is facing a critical security vulnerability that has not been "
            "addressed despite multiple follow-ups."
        ),
        "verbatim_quote": (
            "I reported that vulnerability immediately to the person deploying it and "
            "he answered he would look into it and reply. He did not."
        ),
        "severity": 4,
        "business_function_code": "deployment",
        "jtbd_code": "prevent_fraud",
        "consequence_code": "operational_risk",
    },
    {
        "title": "Phishing legitimacy check",
        "summary": (
            "The user expresses concern over a potential security breach involving "
            "their personal information and questions the legitimacy of the communication."
        ),
        "verbatim_quote": "Is this on the level?",
        "severity": 3,
        "business_function_code": "fraud_prevention",
        "jtbd_code": "prevent_fraud",
        "consequence_code": "customer_loss",
    },
    {
        "title": "Employer ransomware negligence",
        "summary": (
            "The user expresses concern over severe data security negligence by a former "
            "employer, a health insurance company, following a ransomware attack that "
            "compromised customer data."
        ),
        "verbatim_quote": (
            "I believe my former employer may be criminally negligent in their data "
            "security and I'm seeking advice on how to proceed, or if anything can be done."
        ),
        "severity": 4,
        "business_function_code": "fraud_prevention",
        "jtbd_code": "prevent_fraud",
        "consequence_code": "customer_loss",
    },
    {
        "title": "Session fixation in interview app",
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
    {
        "title": "Personal endpoint compromise",
        "summary": (
            "The user is concerned about potential malware on their laptop and seeks "
            "recommendations for security software."
        ),
        "verbatim_quote": (
            "Looks like one of my email accounts has been broken into, and I suspect "
            "malware on my laptop..."
        ),
        "severity": 4,
        "business_function_code": "fraud_prevention",
        "jtbd_code": "prevent_fraud",
        "consequence_code": "operational_risk",
    },
]


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


def _security_corpus_evidence() -> list[ComplaintEvidence]:
    return [_security_evidence(row) for row in SECURITY_CORPUS]


def test_extracts_vulnerability_disclosure_workflow() -> None:
    row = SECURITY_CORPUS[0]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "vulnerability_disclosure_workflow"
    )


def test_extracts_endpoint_security_negligence() -> None:
    row = SECURITY_CORPUS[1]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "endpoint_security_negligence"
    )


def test_extracts_incident_response_coordination() -> None:
    row = SECURITY_CORPUS[3]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "incident_response_coordination"
    )


def test_extracts_session_fixation_exposure() -> None:
    row = SECURITY_CORPUS[4]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "session_fixation_exposure"
    )


def test_extracts_credential_exposure_detection() -> None:
    row = SECURITY_CORPUS[5]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        == "credential_exposure_detection"
    )


def test_thin_phishing_quote_does_not_match_security_fingerprint() -> None:
    row = SECURITY_CORPUS[2]
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote=row["verbatim_quote"],
            summary=row["summary"],
        )
        is None
    )


def test_generic_security_keyword_does_not_match() -> None:
    assert (
        extract_mechanism_fingerprint(
            verbatim_quote="We need better security for our app.",
            summary="General security improvement request.",
        )
        is None
    )


def test_stripe_fingerprint_unchanged_after_security_rules() -> None:
    quote = "I just got kicked off Stripe; classified as high risk."
    assert extract_mechanism_fingerprint(verbatim_quote=quote) == (
        "processor_account_deplatforming"
    )


def test_security_corpus_venture_aware_replay() -> None:
    evidence = [enrich_complaint_evidence(item) for item in _security_corpus_evidence()]

    outcomes = []
    for row, member in zip(SECURITY_CORPUS, evidence, strict=True):
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
            "title": "Internal vuln report reprimanded",
            "mechanism_fingerprint": "vulnerability_disclosure_workflow",
            "singleton_exception": True,
        },
        {
            "title": "Unpatched vulnerability ignored",
            "mechanism_fingerprint": "endpoint_security_negligence",
            "singleton_exception": True,
        },
        {
            "title": "Phishing legitimacy check",
            "mechanism_fingerprint": None,
            "singleton_exception": False,
        },
        {
            "title": "Employer ransomware negligence",
            "mechanism_fingerprint": "incident_response_coordination",
            "singleton_exception": True,
        },
        {
            "title": "Session fixation in interview app",
            "mechanism_fingerprint": "session_fixation_exposure",
            "singleton_exception": True,
        },
        {
            "title": "Personal endpoint compromise",
            "mechanism_fingerprint": "credential_exposure_detection",
            "singleton_exception": True,
        },
    ]
    assert len(patterns) == 5
    assert {p.mechanism_fingerprint for p in patterns} == {
        "vulnerability_disclosure_workflow",
        "endpoint_security_negligence",
        "incident_response_coordination",
        "session_fixation_exposure",
        "credential_exposure_detection",
    }
    assert all(p.singleton_exception_reason for p in patterns)
