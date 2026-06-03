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
        select(Category).where(Category.kind == CategoryKind.DOMAIN.value, Category.code == "saas_b2b")
    )
    persona = await db_session.scalar(
        select(Category).where(Category.kind == CategoryKind.PERSONA.value, Category.code == "founder")
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
        select(Category).where(Category.kind == CategoryKind.DOMAIN.value, Category.code == "saas_b2b")
    )
    persona = await db_session.scalar(
        select(Category).where(Category.kind == CategoryKind.PERSONA.value, Category.code == "founder")
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
        select(Category).where(Category.kind == CategoryKind.DOMAIN.value, Category.code == "saas_b2b")
    )
    persona = await db_session.scalar(
        select(Category).where(Category.kind == CategoryKind.PERSONA.value, Category.code == "founder")
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
