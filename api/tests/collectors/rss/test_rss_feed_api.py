"""API tests for RSS feed management endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_list_and_delete_rss_feed(client: AsyncClient, auth_headers: dict[str, str]):
    feed_url = f"https://example.com/feeds/{uuid4()}.xml"
    create_payload = {
        "name": "Business Signals",
        "feed_url": feed_url,
        "category": "business",
        "enabled": True,
        "polling_interval_sec": 3600,
        "entry_limit": 25,
    }

    create_response = await client.post(
        "/api/v1/rss-feeds",
        headers=auth_headers,
        json=create_payload,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Business Signals"
    assert created["feed_url"] == feed_url
    assert created["category"] == "business"
    assert created["source_id"]

    list_response = await client.get("/api/v1/rss-feeds", headers=auth_headers)
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["total"] >= 1
    assert any(item["id"] == created["id"] for item in listed["items"])

    delete_response = await client.delete(
        f"/api/v1/rss-feeds/{created['id']}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204

    list_after_delete = await client.get("/api/v1/rss-feeds", headers=auth_headers)
    assert all(item["id"] != created["id"] for item in list_after_delete.json()["items"])


@pytest.mark.asyncio
async def test_create_rss_feed_conflict_on_duplicate_url(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    feed_url = f"https://example.com/feeds/{uuid4()}.xml"
    payload = {
        "name": "Industry Watch",
        "feed_url": feed_url,
        "category": "industry",
    }

    first = await client.post("/api/v1/rss-feeds", headers=auth_headers, json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/rss-feeds", headers=auth_headers, json=payload)
    assert second.status_code == 409
