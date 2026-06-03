"""API tests for founder approval workflow."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ApprovalStatus, ReportStatus

pytest_plugins = ["tests.approval.test_approval_service"]


@pytest.mark.asyncio
async def test_list_and_approve_venture_report_via_api(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    ranked_opportunity,
):
    ranking_response = await client.post(
        "/api/v1/executive-ranking/generate?top_n=5",
        headers=auth_headers,
    )
    assert ranking_response.status_code == 201

    report_response = await client.post(
        "/api/v1/executive-reports/generate?top_n=5",
        headers=auth_headers,
    )
    assert report_response.status_code == 201
    report_id = report_response.json()["report_id"]

    list_response = await client.get("/api/v1/approvals", headers=auth_headers)
    assert list_response.status_code == 200
    approvals = list_response.json()
    assert approvals["total"] >= 2

    venture_approval = next(
        item for item in approvals["items"] if item.get("report_id") == report_id
    )
    assert venture_approval["status"] == ApprovalStatus.PENDING.value

    approve_response = await client.post(
        f"/api/v1/approvals/{venture_approval['id']}/approve",
        headers=auth_headers,
        json={"comment": "Approved for founder distribution."},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == ApprovalStatus.APPROVED.value
    assert approve_response.json()["finalized"] is True

    report_get = await client.get(
        f"/api/v1/executive-reports/{report_id}",
        headers=auth_headers,
    )
    assert report_get.status_code == 200
    assert report_get.json()["status"] == ReportStatus.PUBLISHED.value


@pytest.mark.asyncio
async def test_reject_ranking_approval_via_api(
    client: AsyncClient,
    auth_headers: dict[str, str],
    ranked_opportunity,
):
    ranking_response = await client.post(
        "/api/v1/executive-ranking/generate?top_n=5",
        headers=auth_headers,
    )
    assert ranking_response.status_code == 201
    run_id = ranking_response.json()["ranking_run_id"]

    list_response = await client.get(
        "/api/v1/approvals?subject_type=executive_ranking",
        headers=auth_headers,
    )
    approval = next(
        item for item in list_response.json()["items"] if item["executive_ranking_run_id"] == run_id
    )

    reject_response = await client.post(
        f"/api/v1/approvals/{approval['id']}/reject",
        headers=auth_headers,
        json={"comment": "Scores need more agent coverage."},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == ApprovalStatus.REJECTED.value


@pytest.mark.asyncio
async def test_request_research_via_api(
    client: AsyncClient,
    auth_headers: dict[str, str],
    ranked_opportunity,
):
    await client.post("/api/v1/executive-ranking/generate?top_n=5", headers=auth_headers)

    list_response = await client.get(
        "/api/v1/approvals?subject_type=executive_ranking",
        headers=auth_headers,
    )
    approval = list_response.json()["items"][0]

    missing_comment = await client.post(
        f"/api/v1/approvals/{approval['id']}/research",
        headers=auth_headers,
        json={},
    )
    assert missing_comment.status_code == 422

    research_response = await client.post(
        f"/api/v1/approvals/{approval['id']}/research",
        headers=auth_headers,
        json={"comment": "Run additional market research on TAM assumptions."},
    )
    assert research_response.status_code == 200
    assert research_response.json()["status"] == ApprovalStatus.RESEARCH_REQUESTED.value

    detail_response = await client.get("/api/v1/approvals", headers=auth_headers)
    updated = next(item for item in detail_response.json()["items"] if item["id"] == approval["id"])
    assert updated["status"] == ApprovalStatus.RESEARCH_REQUESTED.value
    assert len(updated["decisions"]) == 1
