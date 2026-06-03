"""Integration tests for complaint collection service."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.collection.schemas import RawComplaintBatch, RawComplaintInput
from app.collection.service import ComplaintCollectionService
from app.db.enums import SourceType
from app.db.models.source import Source
from app.exceptions import NotFoundError, ValidationError
from app.repositories import get_repositories


@pytest.fixture
def collection_service(db_session: AsyncSession) -> ComplaintCollectionService:
    return ComplaintCollectionService(get_repositories(db_session))


@pytest.fixture
async def enabled_source(db_session: AsyncSession) -> Source:
    source = Source(
        name=f"collection-source-{uuid4()}",
        source_type=SourceType.REDDIT.value,
        config={"subreddit": "SaaS"},
        enabled=True,
    )
    db_session.add(source)
    await db_session.flush()
    return source


def _sample_item(**overrides) -> RawComplaintInput:
    payload = {
        "external_id": f"ext-{uuid4()}",
        "url": f"https://example.com/posts/{uuid4()}",
        "title": "Pricing is too high",
        "body": "We cannot afford this tool at our stage. It blocks our whole team workflow.",
        "author": "founder123",
        "metadata": {"score": 42, "subreddit": "SaaS"},
    }
    payload.update(overrides)
    return RawComplaintInput(**payload)


@pytest.mark.asyncio
async def test_ingest_inserts_signal_with_metadata(
    collection_service: ComplaintCollectionService,
    enabled_source: Source,
    db_session: AsyncSession,
) -> None:
    item = _sample_item()
    result = await collection_service.ingest(enabled_source.id, item)

    assert result.status == "inserted"
    assert result.signal_id is not None

    signal = await collection_service._repos.signals.get_by_id(result.signal_id)
    assert signal is not None
    assert signal.body == item.body.strip()
    assert signal.signal_metadata["score"] == 42
    assert signal.signal_metadata["collection"]["source_name"] == enabled_source.name
    assert signal.content_hash is not None
    assert signal.processing_status == "pending"


@pytest.mark.asyncio
async def test_ingest_deduplicates_external_id(
    collection_service: ComplaintCollectionService,
    enabled_source: Source,
) -> None:
    item = _sample_item(external_id="duplicate-ext-001")
    first = await collection_service.ingest(enabled_source.id, item)
    second = await collection_service.ingest(
        enabled_source.id,
        _sample_item(
            external_id="duplicate-ext-001",
            url="https://example.com/other-url",
            body="Different body text that is still long enough to pass validation checks.",
        ),
    )

    assert first.status == "inserted"
    assert second.status == "duplicate"
    assert second.reason == "duplicate_external_id"


@pytest.mark.asyncio
async def test_ingest_deduplicates_url(
    collection_service: ComplaintCollectionService,
    enabled_source: Source,
) -> None:
    url = f"https://example.com/shared/{uuid4()}"
    first = await collection_service.ingest(
        enabled_source.id,
        _sample_item(url=url, external_id="url-dedup-1"),
    )
    second = await collection_service.ingest(
        enabled_source.id,
        _sample_item(
            url=url,
            external_id="url-dedup-2",
            body="Another long complaint body that should still be rejected by URL dedup logic.",
        ),
    )

    assert first.status == "inserted"
    assert second.status == "duplicate"
    assert second.reason == "duplicate_url"


@pytest.mark.asyncio
async def test_ingest_deduplicates_content_hash(
    collection_service: ComplaintCollectionService,
    enabled_source: Source,
) -> None:
    body = "Identical normalized complaint text that is definitely long enough for ingestion."
    first = await collection_service.ingest(
        enabled_source.id,
        _sample_item(external_id="hash-1", url="https://example.com/a", body=body),
    )
    second = await collection_service.ingest(
        enabled_source.id,
        _sample_item(external_id="hash-2", url="https://example.com/b", body=body),
    )

    assert first.status == "inserted"
    assert second.status == "duplicate"
    assert second.reason == "duplicate_content_hash"


@pytest.mark.asyncio
async def test_ingest_skips_short_text(
    collection_service: ComplaintCollectionService,
    enabled_source: Source,
) -> None:
    result = await collection_service.ingest(
        enabled_source.id,
        _sample_item(body="too short"),
    )
    assert result.status == "skipped"
    assert result.reason.startswith("text_too_short")


@pytest.mark.asyncio
async def test_ingest_batch_mixed_outcomes(
    collection_service: ComplaintCollectionService,
    enabled_source: Source,
) -> None:
    shared_body = "Shared complaint body long enough to pass validation for batch ingestion."
    batch = RawComplaintBatch(
        source_id=enabled_source.id,
        items=[
            _sample_item(external_id="batch-1"),
            _sample_item(external_id="batch-1", url="https://example.com/dup"),
            _sample_item(body="short"),
            _sample_item(external_id="batch-3", body=shared_body),
            _sample_item(external_id="batch-4", url="https://example.com/x", body=shared_body),
        ],
    )
    result = await collection_service.ingest_batch(batch)

    assert result.inserted == 2
    assert result.duplicates == 2
    assert result.skipped == 1
    assert result.items[4].status == "duplicate"
    assert result.items[4].reason == "duplicate_content_hash"


@pytest.mark.asyncio
async def test_ingest_rejects_disabled_source(
    collection_service: ComplaintCollectionService,
    db_session: AsyncSession,
) -> None:
    source = Source(
        name=f"disabled-{uuid4()}",
        source_type=SourceType.RSS.value,
        config={"url": "https://example.com/feed"},
        enabled=False,
    )
    db_session.add(source)
    await db_session.flush()

    with pytest.raises(ValidationError):
        await collection_service.ingest(source.id, _sample_item())


@pytest.mark.asyncio
async def test_ingest_rejects_missing_source(
    collection_service: ComplaintCollectionService,
) -> None:
    with pytest.raises(NotFoundError):
        await collection_service.ingest(uuid4(), _sample_item())
