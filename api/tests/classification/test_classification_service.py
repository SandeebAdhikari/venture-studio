"""Integration tests for complaint classification agent."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.classification.mock_client import MockClassificationLLMClient
from app.agents.classification.schemas import ClassificationLLMOutput
from app.agents.classification.service import ComplaintClassificationService
from app.collection.schemas import RawComplaintInput
from app.collection.service import ComplaintCollectionService
from app.config import Settings
from app.db.enums import SourceType
from app.db.models.llm_call import LLMCall
from app.db.models.source import Source
from app.repositories import get_repositories
from tests.classification.taxonomy_fixtures import ensure_other_category_seeds


@pytest.fixture(autouse=True)
async def _taxonomy_other_seeds(db_session: AsyncSession) -> None:
    await ensure_other_category_seeds(db_session)


@pytest.fixture
def classification_settings() -> Settings:
    return Settings(
        api_key="test-api-key-for-classification",
        classification_max_retries=2,
        classification_model="mock-classifier",
    )


@pytest.fixture
async def enabled_source(db_session: AsyncSession) -> Source:
    source = Source(
        name=f"classification-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()
    return source


async def _insert_pending_signal(
    db_session: AsyncSession,
    source: Source,
    *,
    title: str = "Pricing is too high",
    body: str = "We cannot afford this tool at our stage. It blocks our whole team workflow.",
) -> UUID:
    collection = ComplaintCollectionService(get_repositories(db_session))
    result = await collection.ingest(
        source.id,
        RawComplaintInput(
            external_id=f"ext-{uuid4()}",
            url=f"https://example.com/posts/{uuid4()}",
            title=title,
            body=body,
            author="founder123",
            metadata={"score": 10},
        ),
    )
    assert result.status == "inserted"
    return result.signal_id


def _valid_output(*, quote: str, is_complaint: bool = True) -> ClassificationLLMOutput:
    return ClassificationLLMOutput(
        is_complaint=is_complaint,
        industry="saas_b2b",
        customer_type="founder",
        problem_category="pricing",
        severity_score=4,
        summary="The user cannot afford the product pricing at their current stage.",
        verbatim_quote=quote,
        confidence=0.92,
        product_mentions=["SomeTool"],
        business_function_code="billing_operations",
        jtbd_code="automate_billing",
        consequence_code="margin_erosion",
    )


@pytest.mark.asyncio
async def test_classify_signal_persists_complaint(
    db_session: AsyncSession,
    enabled_source: Source,
    classification_settings: Settings,
) -> None:
    body = "We cannot afford this tool at our stage. It blocks our whole team workflow."
    signal_id = await _insert_pending_signal(db_session, enabled_source, body=body)
    repos = get_repositories(db_session)
    quote = "We cannot afford this tool at our stage."
    mock = MockClassificationLLMClient([_valid_output(quote=quote)])
    service = ComplaintClassificationService(repos, classification_settings, llm_client=mock)

    result = await service.classify_signal(signal_id)

    assert result.status == "classified"
    assert result.complaint_id is not None
    assert result.classification is not None
    assert result.classification.industry == "saas_b2b"
    assert result.classification.customer_type == "founder"
    assert result.classification.problem_category == "pricing"
    assert result.classification.severity_score == 4

    complaint = await repos.complaints.get_by_signal_id(signal_id)
    assert complaint is not None
    assert complaint.summary == result.classification.summary
    assert complaint.business_function_code == "billing_operations"
    assert complaint.jtbd_code == "automate_billing"
    assert complaint.consequence_code == "margin_erosion"
    assert result.classification.business_function_code == complaint.business_function_code
    assert result.classification.jtbd_code == complaint.jtbd_code
    assert result.classification.consequence_code == complaint.consequence_code

    signal = await repos.signals.get_by_id(signal_id)
    assert signal.processing_status == "classified"


@pytest.mark.asyncio
async def test_classify_signal_persists_founder_signals_through_reload(
    db_session: AsyncSession,
    enabled_source: Source,
    classification_settings: Settings,
) -> None:
    body = "Why are we getting fscked sideways by Stripe, BoA & the customer ?"
    signal_id = await _insert_pending_signal(
        db_session,
        enabled_source,
        title="Ask HN: Stripe and Chargebacks",
        body=body,
    )
    repos = get_repositories(db_session)
    mock = MockClassificationLLMClient(
        [
            ClassificationLLMOutput(
                is_complaint=True,
                industry="fintech",
                customer_type="founder",
                problem_category="pricing",
                severity_score=4,
                summary="Frustration over Stripe chargeback fees and dispute handling.",
                verbatim_quote=body,
                confidence=0.91,
                product_mentions=["Stripe"],
                business_function_code="fraud_prevention",
                jtbd_code="prevent_fraud",
                consequence_code="margin_erosion",
            )
        ]
    )
    service = ComplaintClassificationService(repos, classification_settings, llm_client=mock)

    result = await service.classify_signal(signal_id)

    assert result.status == "classified"
    assert result.complaint_id is not None

    db_session.expire_all()
    complaint = await repos.complaints.get_by_id(result.complaint_id)
    assert complaint is not None
    assert complaint.business_function_code == "fraud_prevention"
    assert complaint.jtbd_code == "prevent_fraud"
    assert complaint.consequence_code == "margin_erosion"


@pytest.mark.asyncio
async def test_classify_signal_normalizes_billing_problem_category_for_deplatforming(
    db_session: AsyncSession,
    enabled_source: Source,
    classification_settings: Settings,
) -> None:
    body = (
        "I just got kicked off Stripe; classified as high risk. "
        "Not really interested in trying to salvage this. "
        "Where else can I go for SaaS billing?"
    )
    signal_id = await _insert_pending_signal(
        db_session,
        enabled_source,
        title="Ask HN: Kicked off Stripe. Where else can I go?",
        body=body,
    )
    repos = get_repositories(db_session)
    mock = MockClassificationLLMClient(
        [
            ClassificationLLMOutput(
                is_complaint=True,
                industry="fintech",
                customer_type="founder",
                problem_category="billing",
                severity_score=4,
                summary="Founder was removed from Stripe as high risk and needs billing alternatives.",
                verbatim_quote=(
                    "I just got kicked off Stripe; classified as high risk. "
                    "Not really interested in trying to salvage this. "
                    "Where else can I go for SaaS billing?"
                ),
                confidence=0.91,
                product_mentions=["Stripe"],
                business_function_code="payment_processor",
                jtbd_code="accept_payments",
                consequence_code="revenue_interruption",
            )
        ]
    )
    service = ComplaintClassificationService(repos, classification_settings, llm_client=mock)

    result = await service.classify_signal(signal_id)

    assert result.status == "classified"
    assert result.complaint_id is not None
    assert result.classification is not None
    assert result.classification.problem_category == "security"

    complaint = await repos.complaints.get_by_signal_id(signal_id)
    assert complaint is not None
    assert complaint.business_function_code == "payment_processor"


@pytest.mark.asyncio
async def test_classify_signal_skips_non_complaint(
    db_session: AsyncSession,
    enabled_source: Source,
    classification_settings: Settings,
) -> None:
    signal_id = await _insert_pending_signal(
        db_session,
        enabled_source,
        title="Weekly discussion thread",
        body="What are you building this week? Share your progress and goals with the community.",
    )
    repos = get_repositories(db_session)
    mock = MockClassificationLLMClient(
        [
            _valid_output(
                quote="What are you building this week?",
                is_complaint=False,
            )
        ]
    )
    service = ComplaintClassificationService(repos, classification_settings, llm_client=mock)

    result = await service.classify_signal(signal_id)

    assert result.status == "skipped"
    assert result.skip_reason == "not_a_complaint"
    assert result.complaint_id is None

    signal = await repos.signals.get_by_id(signal_id)
    assert signal.processing_status == "skipped"
    assert signal.skip_reason == "not_a_complaint"


@pytest.mark.asyncio
async def test_classify_signal_retries_malformed_response(
    db_session: AsyncSession,
    enabled_source: Source,
    classification_settings: Settings,
) -> None:
    body = "Exporting our data takes hours and fails halfway through every time."
    signal_id = await _insert_pending_signal(db_session, enabled_source, body=body)
    repos = get_repositories(db_session)
    retry_quote = "Exporting our data takes hours and fails halfway through every time."
    mock = MockClassificationLLMClient(
        [
            None,
            _valid_output(quote=retry_quote),
        ]
    )
    service = ComplaintClassificationService(repos, classification_settings, llm_client=mock)

    result = await service.classify_signal(signal_id)

    assert result.status == "classified"
    assert mock.call_count == 2
    assert len(result.eval_logs) == 2


@pytest.mark.asyncio
async def test_classify_signal_fails_after_validation_retries(
    db_session: AsyncSession,
    enabled_source: Source,
    classification_settings: Settings,
) -> None:
    body = "Support never responds when our billing is wrong and we cannot get refunds."
    signal_id = await _insert_pending_signal(db_session, enabled_source, body=body)
    repos = get_repositories(db_session)
    mock = MockClassificationLLMClient(
        [
            ClassificationLLMOutput(
                is_complaint=True,
                industry="invalid_industry",
                customer_type="founder",
                problem_category="pricing",
                severity_score=3,
                summary="Support is unresponsive on billing issues for this customer.",
                verbatim_quote="Support never responds when our billing is wrong",
                confidence=0.5,
                business_function_code="billing_operations",
                jtbd_code="automate_billing",
                consequence_code="operational_overhead",
            ),
            ClassificationLLMOutput(
                is_complaint=True,
                industry="invalid_industry",
                customer_type="founder",
                problem_category="pricing",
                severity_score=3,
                summary="Support is unresponsive on billing issues for this customer.",
                verbatim_quote="Support never responds when our billing is wrong",
                confidence=0.5,
                business_function_code="billing_operations",
                jtbd_code="automate_billing",
                consequence_code="operational_overhead",
            ),
        ]
    )
    service = ComplaintClassificationService(repos, classification_settings, llm_client=mock)

    result = await service.classify_signal(signal_id)

    assert result.status == "failed"
    assert mock.call_count == 2

    signal = await repos.signals.get_by_id(signal_id)
    assert signal.processing_status == "failed"


@pytest.mark.asyncio
async def test_classify_signal_logs_llm_calls(
    db_session: AsyncSession,
    enabled_source: Source,
    classification_settings: Settings,
) -> None:
    body = "The onboarding wizard crashes on step two every single time we invite users."
    signal_id = await _insert_pending_signal(db_session, enabled_source, body=body)
    repos = get_repositories(db_session)
    mock = MockClassificationLLMClient(
        [_valid_output(quote="The onboarding wizard crashes on step two every single time")]
    )
    service = ComplaintClassificationService(repos, classification_settings, llm_client=mock)

    await service.classify_signal(signal_id)

    count = await db_session.scalar(
        select(func.count()).select_from(LLMCall).where(LLMCall.entity_id == signal_id)
    )
    assert count == 1

    llm_call = await db_session.scalar(select(LLMCall).where(LLMCall.entity_id == signal_id))
    assert llm_call is not None
    assert llm_call.graph_name == "classify_complaint"
    assert llm_call.status == "success"
    assert llm_call.eval_metadata["parsed"]["problem_category"] == "pricing"


@pytest.mark.asyncio
async def test_classify_pending_batch(
    db_session: AsyncSession,
    enabled_source: Source,
    classification_settings: Settings,
) -> None:
    quote = "Integrations break after every release and we lose a day fixing webhooks."
    body = f"{quote} Our team is stuck firefighting instead of shipping features."
    signal_a = await _insert_pending_signal(db_session, enabled_source, body=body)
    signal_b = await _insert_pending_signal(
        db_session,
        enabled_source,
        title="General news",
        body="Company X raised a Series B round today according to multiple reports.",
    )
    repos = get_repositories(db_session)
    mock = MockClassificationLLMClient(
        [
            ClassificationLLMOutput(
                is_complaint=True,
                industry="devtools",
                customer_type="developer",
                problem_category="integration",
                severity_score=4,
                summary="Integrations break after releases and require manual webhook fixes.",
                verbatim_quote=quote,
                confidence=0.88,
                business_function_code="ci_cd",
                jtbd_code="deploy_software",
                consequence_code="engineering_friction",
            ),
            _valid_output(
                quote="Company X raised a Series B round today",
                is_complaint=False,
            ),
        ]
    )
    service = ComplaintClassificationService(repos, classification_settings, llm_client=mock)

    batch = await service.classify_pending(limit=10)

    assert batch.classified == 1
    assert batch.skipped == 1
    assert batch.failed == 0

    assert (await repos.signals.get_by_id(signal_a)).processing_status == "classified"
    assert (await repos.signals.get_by_id(signal_b)).processing_status == "skipped"


@pytest.mark.asyncio
async def test_classify_signal_html_body_and_other_taxonomy(
    db_session: AsyncSession,
    enabled_source: Source,
    classification_settings: Settings,
) -> None:
    body = (
        "<p>I can&#x27;t keep installing <i>dependencies</i> for every new project.</p> "
        "It wastes hours every week."
    )
    signal_id = await _insert_pending_signal(
        db_session,
        enabled_source,
        title="Ask HN: dev environment pain",
        body=body,
    )
    repos = get_repositories(db_session)
    quote = "I can't keep installing dependencies for every new project."
    mock = MockClassificationLLMClient(
        [
            ClassificationLLMOutput(
                is_complaint=True,
                industry="devtools",
                customer_type="other",
                problem_category="workflow",
                severity_score=3,
                summary="Developer frustrated with repeated dependency setup work.",
                verbatim_quote=quote,
                confidence=0.9,
                business_function_code="deployment",
                jtbd_code="deploy_software",
                consequence_code="engineering_friction",
            )
        ]
    )
    service = ComplaintClassificationService(repos, classification_settings, llm_client=mock)

    result = await service.classify_signal(signal_id)

    assert result.status == "classified"
    assert result.complaint_id is not None
    resolved = await repos.complaints.resolve_category_ids(
        category_code="workflow",
        domain_code="devtools",
        persona_code="other",
    )
    assert resolved is not None
    assert resolved[2].code == "other"
