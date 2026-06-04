#!/usr/bin/env python3
"""One-off production venture validation run capture (not part of test suite)."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx

ROOT = Path(__file__).resolve().parents[2]
API_ENV = ROOT / "api" / ".env"
ROOT_ENV = ROOT / ".env"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_env(ROOT_ENV)
    load_env(API_ENV)
    api_key = os.environ.get("API_KEY", "")
    if not api_key:
        print("ERROR: API_KEY missing", file=sys.stderr)
        return 1
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY missing", file=sys.stderr)
        return 1

    base = os.environ.get("VALIDATION_API_BASE", "http://127.0.0.1:8000")
    founder_id = os.environ.get(
        "FOUNDER_PROFILE_ID", "c52e20d1-a86f-4531-a807-804718c99088"
    )
    out_path = Path(
        os.environ.get(
            "VALIDATION_OUTPUT",
            ROOT / "docs" / "production-venture-validation-run.json",
        )
    )

    headers = {"X-API-Key": api_key}
    timeout = httpx.Timeout(7200.0, connect=30.0)

    with httpx.Client(base_url=base, headers=headers, timeout=timeout) as client:
        ready = client.get("/health/ready")
        ready.raise_for_status()
        budget_before = client.get("/api/v1/budget").json()

        started = time.perf_counter()
        force = os.environ.get("PIPELINE_FORCE", "").lower() in {"1", "true", "yes"}
        run_resp = client.post(
            "/api/v1/pipeline/run",
            json={
                "options": {
                    "stop_on_failure": True,
                    "founder_profile_id": founder_id,
                    "force": force,
                }
            },
        )
        wall_sec = time.perf_counter() - started
        run_resp.raise_for_status()
        run_summary = run_resp.json()
        run_id = run_summary["pipeline_run_id"]

        detail = client.get(f"/api/v1/pipeline/runs/{run_id}").json()
        budget_after = client.get("/api/v1/budget").json()

        ranking = None
        try:
            ranking = client.get("/api/v1/executive-ranking/current").json()
        except httpx.HTTPStatusError:
            ranking = {"error": "no current ranking"}

        report_md = None
        report_meta = None
        try:
            latest = client.get("/api/v1/executive-reports/latest").json()
            report_meta = latest
            rid = latest.get("id")
            if rid is not None:
                report_md = client.get(f"/api/v1/executive-reports/{rid}/markdown").json()
        except httpx.HTTPStatusError as exc:
            report_meta = {"error": str(exc.response.status_code)}

    payload = {
        "captured_at": datetime.now(UTC).isoformat(),
        "api_base": base,
        "wall_seconds": wall_sec,
        "run_summary": run_summary,
        "run_detail": detail,
        "budget_before": budget_before,
        "budget_after": budget_after,
        "ranking": ranking,
        "report_meta": report_meta,
        "report_markdown": report_md,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    print(json.dumps({"ok": True, "run_id": str(run_id), "status": run_summary.get("status"), "wall_seconds": wall_sec, "output": str(out_path)}, indent=2))
    status = run_summary.get("status")
    return 0 if status in {"completed", "success"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
