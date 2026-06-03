"""Integration tests for critical REST endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import CategoryKind, ReviewStatus, SourceType
from app.db.models.category import Category
from app.db.models.signal import Signal
from app.db.models.source import Source


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_sources_require_api_key(client: AsyncClient) -> None:
    response = await client.get("/api/v1/sources")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.get(
        "/api/v1/categories",
        headers=auth_headers,
        params={"kind": CategoryKind.COMPLAINT_CATEGORY.value, "limit": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 11
    assert len(body["items"]) <= 5
    assert body["items"][0]["kind"] == CategoryKind.COMPLAINT_CATEGORY.value


@pytest.mark.asyncio
async def test_create_get_update_source(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    create_payload = {
        "name": f"test-source-{uuid4()}",
        "source_type": SourceType.REDDIT.value,
        "config": {"subreddit": "SaaS", "sort": "new", "limit": 25},
        "enabled": True,
    }
    create_response = await client.post(
        "/api/v1/sources",
        headers=auth_headers,
        json=create_payload,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == create_payload["name"]
    assert created["source_type"] == SourceType.REDDIT.value

    source_id = created["id"]
    get_response = await client.get(f"/api/v1/sources/{source_id}", headers=auth_headers)
    assert get_response.status_code == 200

    patch_response = await client.patch(
        f"/api/v1/sources/{source_id}",
        headers=auth_headers,
        json={"enabled": False},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_create_source_conflict(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    name = f"dup-source-{uuid4()}"
    payload = {
        "name": name,
        "source_type": SourceType.RSS.value,
        "config": {"url": "https://example.com/feed"},
        "enabled": True,
    }
    first = await client.post("/api/v1/sources", headers=auth_headers, json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/sources", headers=auth_headers, json=payload)
    assert second.status_code == 409
    assert second.json()["error"] == "conflict"


@pytest.mark.asyncio
async def test_create_complaint_requires_signal(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "pricing",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value, Category.code == "saas_b2b"
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value, Category.code == "founder"
        )
    )
    assert category is not None and domain is not None and persona is not None

    response = await client.post(
        "/api/v1/complaints",
        headers=auth_headers,
        json={
            "signal_id": str(uuid4()),
            "category_id": str(category.id),
            "domain_id": str(domain.id),
            "persona_id": str(persona.id),
            "summary": "Pricing is too high for small teams.",
            "verbatim_quote": "We can't afford this at our stage.",
            "severity": 4,
            "product_mentions": ["CompetitorX"],
            "llm_model": "gpt-4o-mini",
            "llm_confidence": 0.9,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


@pytest.mark.asyncio
async def test_create_complaint_and_list(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    source = Source(
        name=f"complaint-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://reddit.com/r/SaaS/comments/example",
        title="Tool pricing rant",
        body="The pricing model is impossible for startups.",
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "pricing",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value, Category.code == "saas_b2b"
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value, Category.code == "founder"
        )
    )
    assert category is not None and domain is not None and persona is not None

    create_response = await client.post(
        "/api/v1/complaints",
        headers=auth_headers,
        json={
            "signal_id": str(signal.id),
            "category_id": str(category.id),
            "domain_id": str(domain.id),
            "persona_id": str(persona.id),
            "summary": "Pricing is too high for small teams.",
            "verbatim_quote": "The pricing model is impossible for startups.",
            "severity": 4,
            "product_mentions": ["CompetitorX"],
            "llm_model": "gpt-4o-mini",
            "llm_confidence": 0.9,
        },
    )
    assert create_response.status_code == 201
    complaint_id = create_response.json()["id"]

    detail_response = await client.get(
        f"/api/v1/complaints/{complaint_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["category"]["code"] == "pricing"
    assert detail["domain"]["code"] == "saas_b2b"

    list_response = await client.get(
        "/api/v1/complaints",
        headers=auth_headers,
        params={"min_severity": 3, "category_id": str(category.id)},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_create_and_review_opportunity(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    source = Source(
        name=f"opp-source-{uuid4()}",
        source_type=SourceType.HN_ALGOLIA.value,
        config={"query": "wish"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://news.ycombinator.com/item?id=1",
        body="Someone should build a better CRM.",
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "missing_feature",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value, Category.code == "saas_b2b"
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value, Category.code == "founder"
        )
    )
    assert category is not None and domain is not None and persona is not None

    from app.db.models.complaint import Complaint

    complaint = Complaint(
        signal_id=signal.id,
        category_id=category.id,
        domain_id=domain.id,
        persona_id=persona.id,
        summary="CRM gap for small teams",
        verbatim_quote="Someone should build a better CRM.",
        severity=4,
        llm_model="gpt-4o-mini",
    )
    db_session.add(complaint)
    await db_session.flush()

    create_response = await client.post(
        "/api/v1/opportunities",
        headers=auth_headers,
        json={
            "title": "Lightweight CRM for early-stage founders",
            "problem_statement": "Founders need simple CRM without enterprise overhead.",
            "target_user": "Solo founders and small teams",
            "frequency_signal": "3 similar complaints in 30 days",
            "existing_alternatives": "Spreadsheets and generic CRMs",
            "gap": "No founder-focused lightweight CRM",
            "confidence_score": 0.72,
            "llm_model": "gpt-4o",
            "complaint_ids": [str(complaint.id)],
        },
    )
    assert create_response.status_code == 201
    opportunity = create_response.json()
    assert opportunity["review_status"] == ReviewStatus.NEW.value
    assert str(complaint.id) in opportunity["complaint_ids"]

    review_response = await client.post(
        f"/api/v1/opportunities/{opportunity['id']}/review",
        headers=auth_headers,
        json={"review_status": ReviewStatus.APPROVED.value, "review_notes": "Worth exploring"},
    )
    assert review_response.status_code == 200
    assert review_response.json()["review_status"] == ReviewStatus.APPROVED.value


@pytest.mark.asyncio
async def test_create_and_publish_report(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    create_response = await client.post(
        "/api/v1/reports",
        headers=auth_headers,
        json={
            "report_type": "daily_digest",
            "title": "Daily opportunity digest",
            "summary": "Top opportunities for today",
            "content": {"sections": []},
            "status": "draft",
            "report_metadata": {"generated_by": "test"},
        },
    )
    assert create_response.status_code == 201
    report_id = create_response.json()["id"]

    publish_response = await client.post(
        f"/api/v1/reports/{report_id}/publish",
        headers=auth_headers,
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "published"


@pytest.mark.asyncio
async def test_generate_and_retrieve_top_opportunities_report(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.db.enums import CategoryKind, SourceType
    from app.db.models.category import Category
    from app.db.models.signal import Signal
    from app.db.models.source import Source
    from app.repositories import get_repositories
    from app.schemas.complaint import ComplaintCreate
    from app.schemas.opportunity import OpportunityCreate
    from app.scoring.service import OpportunityScoringService

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "devtools",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "founder",
        )
    )
    assert category is not None and domain is not None and persona is not None

    source = Source(
        name=f"api-report-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://example.com/posts/report-test",
        title="Scheduling pain",
        body="Staff scheduling is broken.",
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category.id,
            domain_id=domain.id,
            persona_id=persona.id,
            summary="Staff scheduling breaks for small teams every week.",
            verbatim_quote="Staff scheduling breaks for small teams every week.",
            severity=5,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )
    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Teams struggle with staff scheduling coordination.",
            target_user="Founders managing hourly teams",
            frequency_signal="Repeated staff scheduling complaints.",
            existing_alternatives="ShiftApp mentioned in evidence.",
            gap="No lightweight staff scheduling workflow.",
            confidence_score=0.88,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )
    await OpportunityScoringService(repos).score_opportunity(opportunity.id)

    generate_response = await client.post(
        "/api/v1/reports/top-opportunities/generate",
        headers=auth_headers,
        params={"limit": 5},
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert "Top Opportunities Report" in body["markdown"]
    assert body["content"]["generated_count"] >= 1
    report_id = body["report_id"]

    get_response = await client.get(f"/api/v1/reports/{report_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["report_type"] == "top_opportunities"

    markdown_response = await client.get(
        f"/api/v1/reports/{report_id}/markdown",
        headers=auth_headers,
    )
    assert markdown_response.status_code == 200
    assert "Staff Scheduling SaaS" in markdown_response.json()["markdown"]


@pytest.mark.asyncio
async def test_get_missing_resource_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get(f"/api/v1/opportunities/{uuid4()}", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


@pytest.mark.asyncio
async def test_generate_and_retrieve_market_research(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.agents.market_research.mock_client import (
        MockMarketResearchLLMClient,
        default_mock_research_output,
    )
    from app.agents.market_research.service import MarketResearchService
    from app.api.deps import get_service_container
    from app.config import get_settings
    from app.db.enums import CategoryKind, SourceType
    from app.db.models.category import Category
    from app.db.models.signal import Signal
    from app.db.models.source import Source
    from app.main import app
    from app.repositories import get_repositories
    from app.schemas.complaint import ComplaintCreate
    from app.schemas.opportunity import OpportunityCreate
    from app.services.container import ServiceContainer

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None

    source = Source(
        name=f"api-research-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://example.com/posts/research-test",
        title="Scheduling pain",
        body="Staff scheduling is broken.",
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category.id,
            domain_id=domain.id,
            persona_id=persona.id,
            summary="Staff scheduling breaks for small teams every week.",
            verbatim_quote="Staff scheduling breaks for small teams every week.",
            severity=5,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )
    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Teams struggle with staff scheduling coordination.",
            target_user="Ops admins managing hourly teams",
            frequency_signal="Repeated staff scheduling complaints.",
            existing_alternatives="ShiftApp mentioned in evidence.",
            gap="No lightweight staff scheduling workflow.",
            confidence_score=0.88,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )

    async def override_services() -> ServiceContainer:
        container = ServiceContainer(repos)
        settings = get_settings()
        container.market_research = MarketResearchService(
            repos,
            settings,
            llm_client=MockMarketResearchLLMClient([default_mock_research_output()]),
        )
        return container

    app.dependency_overrides[get_service_container] = override_services

    generate_response = await client.post(
        f"/api/v1/market-research/opportunities/{opportunity.id}/generate",
        headers=auth_headers,
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert body["status"] == "completed"
    assert body["market_brief_id"] is not None
    assert body["draft"]["tam_usd"] == pytest.approx(4_500_000_000)

    brief_id = body["market_brief_id"]
    get_response = await client.get(f"/api/v1/market-research/{brief_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["opportunity_id"] == str(opportunity.id)
    assert get_response.json()["is_current"] is True

    current_response = await client.get(
        f"/api/v1/market-research/opportunities/{opportunity.id}/current",
        headers=auth_headers,
    )
    assert current_response.status_code == 200
    assert current_response.json()["id"] == brief_id

    history_response = await client.get(
        f"/api/v1/market-research/opportunities/{opportunity.id}/history",
        headers=auth_headers,
    )
    assert history_response.status_code == 200
    assert len(history_response.json()) == 1


@pytest.mark.asyncio
async def test_generate_and_retrieve_competitor_intelligence(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.agents.competitor_intelligence.mock_client import (
        MockCompetitorIntelligenceLLMClient,
        default_mock_competitor_output,
    )
    from app.agents.competitor_intelligence.service import CompetitorIntelligenceService
    from app.api.deps import get_service_container
    from app.config import get_settings
    from app.db.enums import CategoryKind, SourceType
    from app.db.models.category import Category
    from app.db.models.signal import Signal
    from app.db.models.source import Source
    from app.main import app
    from app.repositories import get_repositories
    from app.schemas.complaint import ComplaintCreate
    from app.schemas.opportunity import OpportunityCreate
    from app.services.container import ServiceContainer

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None

    source = Source(
        name=f"api-competitor-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://example.com/posts/competitor-test",
        title="Scheduling pain",
        body="Staff scheduling is broken.",
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category.id,
            domain_id=domain.id,
            persona_id=persona.id,
            summary="Staff scheduling breaks every week when using ShiftApp.",
            verbatim_quote="Staff scheduling breaks every week when using ShiftApp.",
            severity=5,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )
    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Teams struggle with staff scheduling coordination.",
            target_user="Ops admins managing hourly teams",
            frequency_signal="Repeated staff scheduling complaints.",
            existing_alternatives="ShiftApp mentioned in evidence.",
            gap="No lightweight staff scheduling workflow.",
            confidence_score=0.88,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )

    async def override_services() -> ServiceContainer:
        container = ServiceContainer(repos)
        settings = get_settings()
        container.competitor_intelligence = CompetitorIntelligenceService(
            repos,
            settings,
            llm_client=MockCompetitorIntelligenceLLMClient([default_mock_competitor_output()]),
        )
        return container

    app.dependency_overrides[get_service_container] = override_services

    generate_response = await client.post(
        f"/api/v1/competitor-intelligence/opportunities/{opportunity.id}/generate",
        headers=auth_headers,
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert body["status"] == "completed"
    assert body["competitor_analysis_id"] is not None
    assert len(body["draft"]["competitors"]) == 2
    assert body["draft"]["evaluation_metrics"]["competitor_count"] == 2

    analysis_id = body["competitor_analysis_id"]
    get_response = await client.get(
        f"/api/v1/competitor-intelligence/{analysis_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["opportunity_id"] == str(opportunity.id)
    assert len(detail["profiles"]) == 2
    assert detail["profiles"][0]["pricing_model"]["model_type"] == "subscription"

    current_response = await client.get(
        f"/api/v1/competitor-intelligence/opportunities/{opportunity.id}/current",
        headers=auth_headers,
    )
    assert current_response.status_code == 200
    assert current_response.json()["id"] == analysis_id


@pytest.mark.asyncio
async def test_generate_and_retrieve_customer_research(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.agents.customer_research.mock_client import (
        MockCustomerResearchLLMClient,
        default_mock_customer_research_output,
    )
    from app.agents.customer_research.service import CustomerResearchService
    from app.api.deps import get_service_container
    from app.config import get_settings
    from app.db.enums import CategoryKind, SourceType
    from app.db.models.category import Category
    from app.db.models.signal import Signal
    from app.db.models.source import Source
    from app.main import app
    from app.repositories import get_repositories
    from app.schemas.complaint import ComplaintCreate
    from app.schemas.opportunity import OpportunityCreate
    from app.services.container import ServiceContainer

    quote = "Staff scheduling breaks every week when employees swap shifts without notice."

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None

    source = Source(
        name=f"api-customer-research-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://example.com/posts/customer-research-test",
        title="Scheduling pain",
        body=quote,
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category.id,
            domain_id=domain.id,
            persona_id=persona.id,
            summary="Staff scheduling chaos from last-minute shift changes.",
            verbatim_quote=quote,
            severity=4,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )
    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Teams struggle with staff scheduling coordination.",
            target_user="Ops admins managing hourly teams",
            frequency_signal="Repeated staff scheduling complaints.",
            existing_alternatives="ShiftApp mentioned in evidence.",
            gap="No lightweight staff scheduling workflow.",
            confidence_score=0.88,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )

    async def override_services() -> ServiceContainer:
        container = ServiceContainer(repos)
        settings = get_settings()
        container.customer_research = CustomerResearchService(
            repos,
            settings,
            llm_client=MockCustomerResearchLLMClient([default_mock_customer_research_output()]),
        )
        return container

    app.dependency_overrides[get_service_container] = override_services

    generate_response = await client.post(
        f"/api/v1/customer-research/opportunities/{opportunity.id}/generate",
        headers=auth_headers,
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert body["status"] == "completed"
    assert body["draft"]["pain_score"] == 82
    assert body["draft"]["cares_verdict"] == "yes"

    research_id = body["customer_research_id"]
    get_response = await client.get(
        f"/api/v1/customer-research/{research_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["opportunity_id"] == str(opportunity.id)
    assert len(detail["evidence"]) == 3
    assert detail["validation_metrics"]["cares_verdict"] == "yes"


@pytest.mark.asyncio
async def test_generate_and_retrieve_revenue_validation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.agents.revenue_validation.mock_client import (
        MockRevenueValidationLLMClient,
        default_mock_revenue_validation_output,
    )
    from app.agents.revenue_validation.service import RevenueValidationService
    from app.api.deps import get_service_container
    from app.config import get_settings
    from app.db.enums import CategoryKind, SourceType
    from app.db.models.category import Category
    from app.db.models.signal import Signal
    from app.db.models.source import Source
    from app.main import app
    from app.repositories import get_repositories
    from app.schemas.complaint import ComplaintCreate
    from app.schemas.opportunity import OpportunityCreate
    from app.services.container import ServiceContainer

    quote = "Staff scheduling breaks every week when employees swap shifts without notice."

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None

    source = Source(
        name=f"api-revenue-validation-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://example.com/posts/revenue-validation-test",
        title="Scheduling pain",
        body=quote,
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category.id,
            domain_id=domain.id,
            persona_id=persona.id,
            summary="Staff scheduling chaos from last-minute shift changes.",
            verbatim_quote=quote,
            severity=4,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )
    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Teams struggle with staff scheduling coordination.",
            target_user="Ops admins managing hourly teams",
            frequency_signal="Repeated staff scheduling complaints.",
            existing_alternatives="ShiftApp mentioned in evidence.",
            gap="No lightweight staff scheduling workflow.",
            confidence_score=0.88,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )

    async def override_services() -> ServiceContainer:
        container = ServiceContainer(repos)
        settings = get_settings()
        container.revenue_validation = RevenueValidationService(
            repos,
            settings,
            llm_client=MockRevenueValidationLLMClient(
                [default_mock_revenue_validation_output(include_competitor_pricing=False)]
            ),
        )
        return container

    app.dependency_overrides[get_service_container] = override_services

    generate_response = await client.post(
        f"/api/v1/revenue-validation/opportunities/{opportunity.id}/generate",
        headers=auth_headers,
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert body["status"] == "completed"
    assert body["draft"]["willingness_to_pay_score"] == 74
    assert body["draft"]["revenue_confidence_score"] == 68

    validation_id = body["revenue_validation_id"]
    get_response = await client.get(
        f"/api/v1/revenue-validation/{validation_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["opportunity_id"] == str(opportunity.id)
    assert len(detail["evidence"]) == 3
    assert detail["evaluation_metrics"]["evaluation_readiness_score"] > 0


@pytest.mark.asyncio
async def test_generate_and_retrieve_product_strategy(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.agents.product_strategy.mock_client import (
        MockProductStrategyLLMClient,
        default_mock_product_strategy_output,
    )
    from app.agents.product_strategy.service import ProductStrategyService
    from app.api.deps import get_service_container
    from app.config import get_settings
    from app.db.enums import CategoryKind, SourceType
    from app.db.models.category import Category
    from app.db.models.signal import Signal
    from app.db.models.source import Source
    from app.main import app
    from app.repositories import get_repositories
    from app.schemas.complaint import ComplaintCreate
    from app.schemas.opportunity import OpportunityCreate
    from app.services.container import ServiceContainer

    quote = "Staff scheduling breaks every week when employees swap shifts without notice."

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None

    source = Source(
        name=f"api-product-strategy-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://example.com/posts/product-strategy-test",
        title="Scheduling pain",
        body=quote,
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category.id,
            domain_id=domain.id,
            persona_id=persona.id,
            summary="Staff scheduling chaos from last-minute shift changes.",
            verbatim_quote=quote,
            severity=4,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )
    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Teams struggle with staff scheduling coordination.",
            target_user="Ops admins managing hourly teams",
            frequency_signal="Repeated staff scheduling complaints.",
            existing_alternatives="ShiftApp mentioned in evidence.",
            gap="No lightweight staff scheduling workflow.",
            confidence_score=0.88,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )

    async def override_services() -> ServiceContainer:
        container = ServiceContainer(repos)
        settings = get_settings()
        container.product_strategy = ProductStrategyService(
            repos,
            settings,
            llm_client=MockProductStrategyLLMClient([default_mock_product_strategy_output()]),
        )
        return container

    app.dependency_overrides[get_service_container] = override_services

    generate_response = await client.post(
        f"/api/v1/product-strategy/opportunities/{opportunity.id}/generate",
        headers=auth_headers,
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert body["status"] == "completed"
    assert len(body["draft"]["core_features"]) == 3
    assert len(body["draft"]["roadmap"]) == 3

    strategy_id = body["product_strategy_id"]
    get_response = await client.get(
        f"/api/v1/product-strategy/{strategy_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["opportunity_id"] == str(opportunity.id)
    assert len(detail["evidence"]) == 3
    assert detail["planning_metrics"]["planning_readiness_score"] > 0
    assert detail["estimated_timeline"]["total_weeks"] == 13


@pytest.mark.asyncio
async def test_generate_and_retrieve_go_to_market_plan(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.agents.go_to_market.mock_client import (
        MockGoToMarketLLMClient,
        default_mock_go_to_market_output,
    )
    from app.agents.go_to_market.service import GoToMarketService
    from app.api.deps import get_service_container
    from app.config import get_settings
    from app.db.enums import CategoryKind, SourceType
    from app.db.models.category import Category
    from app.db.models.signal import Signal
    from app.db.models.source import Source
    from app.main import app
    from app.repositories import get_repositories
    from app.schemas.complaint import ComplaintCreate
    from app.schemas.opportunity import OpportunityCreate
    from app.services.container import ServiceContainer

    quote = "Staff scheduling breaks every week when employees swap shifts without notice."

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None

    source = Source(
        name=f"api-go-to-market-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://example.com/posts/go-to-market-test",
        title="Scheduling pain",
        body=quote,
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category.id,
            domain_id=domain.id,
            persona_id=persona.id,
            summary="Staff scheduling chaos from last-minute shift changes.",
            verbatim_quote=quote,
            severity=4,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )
    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Teams struggle with staff scheduling coordination.",
            target_user="Ops admins managing hourly teams",
            frequency_signal="Repeated staff scheduling complaints.",
            existing_alternatives="ShiftApp mentioned in evidence.",
            gap="No lightweight staff scheduling workflow.",
            confidence_score=0.88,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )

    async def override_services() -> ServiceContainer:
        container = ServiceContainer(repos)
        settings = get_settings()
        container.go_to_market = GoToMarketService(
            repos,
            settings,
            llm_client=MockGoToMarketLLMClient([default_mock_go_to_market_output()]),
        )
        return container

    app.dependency_overrides[get_service_container] = override_services

    generate_response = await client.post(
        f"/api/v1/go-to-market/opportunities/{opportunity.id}/generate",
        headers=auth_headers,
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert body["status"] == "completed"
    assert body["draft"]["confidence_score"] == 72
    assert body["draft"]["estimated_cac_usd"] == 135.0
    assert len(body["draft"]["acquisition_roadmap"]) == 3

    plan_id = body["gtm_plan_id"]
    get_response = await client.get(
        f"/api/v1/go-to-market/{plan_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["opportunity_id"] == str(opportunity.id)
    assert len(detail["evidence"]) == 3
    assert detail["ranking_metrics"]["gtm_readiness_score"] > 0
    assert len(detail["customer_personas"]) == 2


@pytest.mark.asyncio
async def test_generate_and_retrieve_growth_evaluation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.agents.growth_strategy.mock_client import (
        MockGrowthStrategyLLMClient,
        default_mock_growth_strategy_output,
    )
    from app.agents.growth_strategy.service import GrowthStrategyService
    from app.api.deps import get_service_container
    from app.config import get_settings
    from app.db.enums import CategoryKind, SourceType
    from app.db.models.category import Category
    from app.db.models.signal import Signal
    from app.db.models.source import Source
    from app.main import app
    from app.repositories import get_repositories
    from app.schemas.complaint import ComplaintCreate
    from app.schemas.opportunity import OpportunityCreate
    from app.services.container import ServiceContainer

    quote = "Staff scheduling breaks every week when employees swap shifts without notice."

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None

    source = Source(
        name=f"api-growth-strategy-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://example.com/posts/growth-strategy-test",
        title="Scheduling pain",
        body=quote,
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category.id,
            domain_id=domain.id,
            persona_id=persona.id,
            summary="Staff scheduling chaos from last-minute shift changes.",
            verbatim_quote=quote,
            severity=4,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )
    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Teams struggle with staff scheduling coordination.",
            target_user="Ops admins managing hourly teams",
            frequency_signal="Repeated staff scheduling complaints.",
            existing_alternatives="ShiftApp mentioned in evidence.",
            gap="No lightweight staff scheduling workflow.",
            confidence_score=0.88,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )

    async def override_services() -> ServiceContainer:
        container = ServiceContainer(repos)
        settings = get_settings()
        container.growth_strategy = GrowthStrategyService(
            repos,
            settings,
            llm_client=MockGrowthStrategyLLMClient([default_mock_growth_strategy_output()]),
        )
        return container

    app.dependency_overrides[get_service_container] = override_services

    generate_response = await client.post(
        f"/api/v1/growth-strategy/opportunities/{opportunity.id}/generate",
        headers=auth_headers,
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert body["status"] == "completed"
    assert body["draft"]["growth_score"] == 78
    assert body["draft"]["scalability_score"] == 71
    assert body["draft"]["risk_score"] == 42
    assert len(body["draft"]["growth_roadmap"]) == 3

    evaluation_id = body["growth_evaluation_id"]
    get_response = await client.get(
        f"/api/v1/growth-strategy/{evaluation_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["opportunity_id"] == str(opportunity.id)
    assert len(detail["evidence"]) == 3
    assert detail["evaluation_metrics"]["growth_readiness_score"] > 0
    assert detail["seo_potential"]["score"] == 74


@pytest.mark.asyncio
async def test_generate_and_retrieve_human_proxy_evaluation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.agents.human_proxy.mock_client import (
        MockHumanProxyLLMClient,
        default_mock_human_proxy_output,
    )
    from app.agents.human_proxy.service import HumanProxyService
    from app.api.deps import get_service_container
    from app.config import get_settings
    from app.main import app
    from app.repositories import get_repositories
    from app.schemas.complaint import ComplaintCreate
    from app.schemas.opportunity import OpportunityCreate
    from app.services.container import ServiceContainer

    quote = "Staff scheduling breaks every week when employees swap shifts without notice."

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None

    source = Source(
        name=f"api-human-proxy-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()

    signal = Signal(
        source_id=source.id,
        external_id=f"ext-{uuid4()}",
        url="https://example.com/posts/human-proxy-test",
        title="Scheduling pain",
        body=quote,
        processing_status="classified",
    )
    db_session.add(signal)
    await db_session.flush()

    repos = get_repositories(db_session)
    complaint = await repos.complaints.create(
        ComplaintCreate(
            signal_id=signal.id,
            category_id=category.id,
            domain_id=domain.id,
            persona_id=persona.id,
            summary="Staff scheduling chaos from last-minute shift changes.",
            verbatim_quote=quote,
            severity=4,
            product_mentions=["ShiftApp"],
            llm_model="mock-classifier",
            llm_confidence=0.9,
        )
    )
    opportunity = await repos.opportunities.create(
        OpportunityCreate(
            title="Staff Scheduling SaaS",
            problem_statement="Teams struggle with staff scheduling coordination.",
            target_user="Ops admins managing hourly teams",
            frequency_signal="Repeated staff scheduling complaints.",
            existing_alternatives="ShiftApp mentioned in evidence.",
            gap="No lightweight staff scheduling workflow.",
            confidence_score=0.88,
            llm_model="mock-generator",
            complaint_ids=[complaint.id],
        )
    )

    async def override_services() -> ServiceContainer:
        container = ServiceContainer(repos)
        settings = get_settings()
        container.human_proxy = HumanProxyService(
            repos,
            settings,
            llm_client=MockHumanProxyLLMClient([default_mock_human_proxy_output()]),
        )
        return container

    app.dependency_overrides[get_service_container] = override_services

    profiles_response = await client.get(
        "/api/v1/human-proxy/founder-profiles",
        headers=auth_headers,
    )
    assert profiles_response.status_code == 200
    profiles = profiles_response.json()
    assert len(profiles) >= 1
    assert any(profile["is_default"] for profile in profiles)

    generate_response = await client.post(
        f"/api/v1/human-proxy/opportunities/{opportunity.id}/generate",
        headers=auth_headers,
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert body["status"] == "completed"
    assert body["draft"]["founder_fit_score"] == 82
    assert body["draft"]["feasibility_score"] == 76
    assert body["draft"]["recommendation"] == "pursue"

    evaluation_id = body["human_proxy_evaluation_id"]
    get_response = await client.get(
        f"/api/v1/human-proxy/{evaluation_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200
    detail = get_response.json()
    assert detail["opportunity_id"] == str(opportunity.id)
    assert len(detail["evidence"]) == 3
    assert detail["evaluation_metrics"]["ranking_score"] > 0

    history_response = await client.get(
        f"/api/v1/human-proxy/opportunities/{opportunity.id}/history",
        headers=auth_headers,
    )
    assert history_response.status_code == 200
    assert len(history_response.json()) == 1


@pytest.mark.asyncio
async def test_generate_executive_ranking_api(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.repositories import get_repositories
    from tests.ranking.test_executive_ranking_service import (
        AgentScoreProfile,
        _create_opportunity,
        _seed_agent_outputs,
    )

    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None

    opportunity = await _create_opportunity(
        db_session,
        (category.id, domain.id, persona.id),
        title="Executive Ranking API Opportunity",
    )
    await _seed_agent_outputs(
        repos,
        opportunity.id,
        default_profile.id,
        AgentScoreProfile(pain=85, founder_fit=88),
    )

    generate_response = await client.post(
        "/api/v1/executive-ranking/generate?top_n=5",
        headers=auth_headers,
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert body["ranked_opportunity_count"] >= 1
    assert len(body["top_opportunities"]) >= 1
    assert body["top_opportunities"][0]["final_opportunity_score"] > 0
    assert body["top_opportunities"][0]["pain_score"] is not None

    current_response = await client.get(
        "/api/v1/executive-ranking/current",
        headers=auth_headers,
    )
    assert current_response.status_code == 200
    current = current_response.json()
    assert current["is_current"] is True
    assert len(current["top_opportunities"]) >= 1


@pytest.mark.asyncio
async def test_generate_and_download_venture_report(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    from app.repositories import get_repositories
    from tests.ranking.test_executive_ranking_service import (
        AgentScoreProfile,
        _create_opportunity,
        _seed_agent_outputs,
    )

    repos = get_repositories(db_session)
    default_profile = await repos.founder_profiles.get_default()
    assert default_profile is not None

    category = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.COMPLAINT_CATEGORY.value,
            Category.code == "workflow",
        )
    )
    domain = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.DOMAIN.value,
            Category.code == "saas_b2b",
        )
    )
    persona = await db_session.scalar(
        select(Category).where(
            Category.kind == CategoryKind.PERSONA.value,
            Category.code == "ops_admin",
        )
    )
    assert category is not None and domain is not None and persona is not None

    opportunity = await _create_opportunity(
        db_session,
        (category.id, domain.id, persona.id),
        title="Venture Report API Opportunity",
    )
    await _seed_agent_outputs(
        repos,
        opportunity.id,
        default_profile.id,
        AgentScoreProfile(pain=86, founder_fit=90),
    )

    await client.post(
        "/api/v1/executive-ranking/generate?top_n=5",
        headers=auth_headers,
    )

    generate_response = await client.post(
        "/api/v1/executive-reports/generate?top_n=5&generate_ranking_if_missing=false",
        headers=auth_headers,
    )
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert "Venture Recommendation Report" in body["markdown"]
    assert body["content"]["generated_count"] >= 1
    assert "### MVP plan" in body["markdown"]

    report_id = body["report_id"]
    markdown_response = await client.get(
        f"/api/v1/executive-reports/{report_id}/markdown",
        headers=auth_headers,
    )
    assert markdown_response.status_code == 200
    assert "Venture Recommendation Report" in markdown_response.json()["markdown"]

    download_response = await client.get(
        f"/api/v1/executive-reports/{report_id}/download",
        headers=auth_headers,
    )
    assert download_response.status_code == 200
    assert download_response.headers["content-disposition"].startswith("attachment;")
    assert "Venture Recommendation Report" in download_response.text

    latest_response = await client.get(
        "/api/v1/executive-reports/latest",
        headers=auth_headers,
    )
    assert latest_response.status_code == 200
    assert latest_response.json()["id"] == report_id
