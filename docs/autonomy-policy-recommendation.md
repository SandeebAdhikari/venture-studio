# Autonomy Policy — Formal Recommendation

**Production Readiness Remediation #13**  
**Status:** Awaiting founder approval — **no code or configuration changes until this decision is accepted.**  
**Date:** June 2026  
**Prior analysis:** [autonomy-policy-review.md](./autonomy-policy-review.md) (remediation #9, checkpoint map)

---

## 1. Decision required

The largest remaining production-readiness deduction is **autonomy policy**: the platform runs the full pipeline autonomously, but **venture publication** is gated by `REQUIRE_FOUNDER_APPROVAL=true` (default). You must choose an explicit operating model for production.

| Option | Summary |
|--------|---------|
| **Model A** | Human-in-the-loop — founder approves before venture reports are `published` |
| **Model B** | Human-on-the-loop — system auto-publishes; founder supervises and can reject/archive after |
| **Model C** | Fully autonomous — no approval workflow; publication on schedule with infra/budget guards only |

**Recommended production default:** **Model A** (retain current default and architecture).

---

## 2. Current state (verified, no code changes)

### 2.1 Configuration

| Setting | Default | Effect |
|---------|---------|--------|
| `REQUIRE_FOUNDER_APPROVAL` | `true` | `ApprovalService.enabled` — gates venture report publication and creates approval records |

CI and some tests use `false` for determinism; production is expected to use `true`.

### 2.2 What runs without humans

All **14 pipeline stages** complete in one `run_pipeline` job without waiting on approval:

| Funnel stage (product) | Pipeline / system | Human gate? |
|------------------------|-------------------|-------------|
| Internet | Collect (Reddit, RSS, HN) | No |
| Problems | Classify | No |
| Opportunities | Generate + score | No |
| Validation | Research agents (8) + revenue validation | No (LLM budget may block) |
| Research | Same agent stages | No |
| Ranking | Executive ranking (stage 13) | **Soft** — runs and becomes `is_current`; approval record only |
| Business plan | Venture report generation (stage 14) | **Hard** — content written; `status=draft` until approve |
| Human review | Dashboard `/approvals` | **Required** for publication (Model A) |

### 2.3 Approval workflow (`ApprovalService`)

- **Venture report:** `VentureReportService` forces `publish=False` when approval enabled → `reports.status=draft` → `create_for_venture_report()` → founder `POST /approvals/{id}/approve` → `reports.publish()`.
- **Executive ranking:** Ranking persisted with `is_current=true`; approval updates metadata (`approved` / `rejected` / `research_requested`) — **does not hide ranking from dashboard**.
- **Reject / request research:** No auto re-run; manual follow-up.

### 2.4 Publication flow

```
run_pipeline → VENTURE_REPORT stage → draft report + pending approval_request
Founder approve → published → DashboardSummary.latest_venture (published only)
```

`DashboardService.get_summary` filters venture reports to `ReportStatus.PUBLISHED`. The reports page lists drafts and published items.

### 2.5 Dashboard approval experience

- **Page:** `/approvals` — polling list, filters (status, subject type), detail panel.
- **Actions:** Approve, reject, request research (optional comment); BFF + RBAC (founder/admin).
- **E2E:** `web/e2e/approvals-mutations.spec.ts` covers draft visibility and mutations (seed requires `REQUIRE_FOUNDER_APPROVAL=true`).
- **Gap:** No dedicated alert for “pending approval > N hours” (process/ops gap, not UI).

### 2.6 Parallel triage (not publication)

`opportunities.review_status` (`new`, `approved`, `rejected`, `deferred`) is **informational** — not wired to pipeline or venture publication.

---

## 3. AVS funnel alignment

Target chain from product objectives:

```text
Internet → Problems → Opportunities → Validation → Research → Ranking → Business Plan → Human Review
```

| Model | Where “Human Review” sits | Funnel fit |
|-------|---------------------------|------------|
| **A** | After business plan **generation**, before **publication** | **Strong** — automation through ranking + report draft; explicit founder decision at the end |
| **B** | After publication (supervisory) | **Moderate** — matches “review” as monitoring, not gate; shifts founder role |
| **C** | Optional / periodic calibration only | **Weak** for stated solo-founder decision-support product |

**Architecture today implements Model A:** stages 1–12 and report **generation** are autonomous; **Human Review** is implemented as the approval boundary on venture **publication**, not on data collection or research execution.

**Vision alignment** ([vision.md](./vision.md)): principle 3 — “Human-in-the-loop by default”; non-goal — “autonomous external actions.” Model A is the intended product contract.

---

## 4. Operating model analysis

### 4.1 Model A — Human-in-the-loop (recommended)

**Definition:** Pipeline and agents run unattended; founder **must approve** venture reports to publish. Rankings are visible before sign-off (known asymmetry).

| Dimension | Assessment |
|-----------|------------|
| **Operational impact** | 15–30 min/day on `/approvals` after nightly run; summary dashboard stale until approve; ranking/opportunity pages usable immediately |
| **Failure modes** | Founder absence → queue growth, no `latest_venture` on summary; false sense of “pipeline broken” when run succeeded; ranking visible while “pending” may confuse |
| **Risk profile** | **Low** publication risk; **low** reputational risk; **medium** ops SLA risk (human dependency) |
| **Implementation complexity** | **None** — shipped (`approval.py`, venture service, dashboard, E2E) |
| **Production-readiness** | **Highest** — matches audit intent; “not fully autonomous” is **by design**, not a defect |

### 4.2 Model B — Human-on-the-loop

**Definition:** Auto-publish venture reports (and optionally treat rankings as canonical without sign-off); founder monitors, rejects, or requests follow-up **after** publication.

| Dimension | Assessment |
|-----------|------------|
| **Operational impact** | Near-zero daily gate time; requires discipline to review new publications; dashboard summary always current |
| **Failure modes** | Bad LLM/ranking output published before review; reject-after-publish needs retract/archive semantics (partial today); `request_research` less meaningful post-publish; alert fatigue if every nightly run notifies |
| **Risk profile** | **Medium–high** decision quality and trust risk without added guardrails |
| **Implementation complexity** | **Medium** — toggle exists (`REQUIRE_FOUNDER_APPROVAL=false`) but **not production-grade B** without: publication webhooks/alerts, `published_by` audit field, archive/retract API, dashboard “auto-published” labeling, optional cooling period, ranking visibility policy |
| **Production-readiness** | **Partial** — unblocks “autonomous publication” metric but **lowers** governance score unless monitoring/rollback added |

### 4.3 Model C — Fully autonomous

**Definition:** No founder approval in the operational loop; nightly outputs are published artifacts; humans only tune sources, budget, and config.

| Dimension | Assessment |
|-----------|------------|
| **Operational impact** | No approval queue; founder role shifts to weekly/monthly calibration |
| **Failure modes** | Systematic quality drift; hallucinations in venture markdown treated as decisions; no human proxy for accountability; external sharing of reports without review |
| **Risk profile** | **High** for a solo founder using outputs as venture decisions |
| **Implementation complexity** | **Low** for toggle; **High** for safe production (confidence gates, anomaly detection, auto-hold rules) — **not present** in codebase |
| **Production-readiness** | **Misleading** if scored as “fully autonomous” without quality automation — contradicts vision non-goals |

---

## 5. Comparison matrix

| Criterion | Model A | Model B | Model C |
|-----------|---------|---------|---------|
| Venture publication | After approve | Auto + supervise | Auto |
| Pipeline `run_pipeline` | Unchanged | Unchanged | Unchanged |
| Executive ranking dashboard | Immediate (`is_current`) | Same | Same |
| Audit trail | Strong | Needs post-publish audit | Minimal |
| Founder daily time | Required (approvals) | Monitoring | ~0 |
| Code ready today | **Yes** | Toggle only | Toggle only |
| E2E / runbook fit | **Yes** | Needs new flows | Simpler path |
| PR audit “autonomy” deduction | Intentional partial | Unblocked with risk | Unblocked with high risk |
| Funnel “Human Review” | Terminal gate | Post-hoc review | Absent |

---

## 6. Recommendation

### 6.1 Primary recommendation

**Adopt Model A (Human-in-the-loop) as the production autonomy policy.**

- Keep `REQUIRE_FOUNDER_APPROVAL=true` in production.
- Treat the audit deduction (“cannot publish without founder”) as **accepted product risk**, not a blocker to ship.
- Document founder SLA: review pending venture report approvals within **24 hours** of nightly run (operational process).

### 6.2 Do not adopt (without explicit product pivot)

- **Model C** for production — conflicts with vision, approval service design, and dashboard workflows.
- **Model B via flag flip only** (`REQUIRE_FOUNDER_APPROVAL=false`) — equivalent to C for reports without safety tooling.

### 6.3 Optional future path (only if business requires less friction)

Evolve to **Model B** in a **separate approved remediation**, not by disabling the flag alone:

1. New explicit `AUTO_PUBLISH_VENTURE_REPORTS` (decoupled from disabling audit workflow).
2. Alert on each publication (Slack/webhook) with summary + link.
3. Report archive/retract and dashboard badges (“published by automation”).
4. Policy for rankings: hide or label unapproved `is_current` runs.

---

## 7. Migration plan

**Applies only if you reject Model A and approve Model B or C.**

### Phase 0 — Decision (current)

| Step | Action | Code? |
|------|--------|-------|
| 0.1 | Approve Model A, B, or C in writing | No |
| 0.2 | Update production `.env` policy doc | No |

### Phase A — Stay on Model A (recommended)

| Step | Action | Code? |
|------|--------|-------|
| A.1 | Confirm production `REQUIRE_FOUNDER_APPROVAL=true` | Config only (after approval) |
| A.2 | Add ops alert: pending venture approval > 24h | Small (#14+) |
| A.3 | Document ranking pre-approval asymmetry in founder runbook | Docs |
| A.4 | Optional: dashboard badge “pending publication” on summary | Small UX |

**Migration risk:** None — no behavior change.

### Phase B — Model B (if approved later)

| Step | Action | Dependency |
|------|--------|------------|
| B.1 | Implement `AUTO_PUBLISH_VENTURE_REPORTS` + keep approval records for audit | Config + service |
| B.2 | Publication alert integration (alerting #7) | Webhook/Slack |
| B.3 | `reports.published_by`, `auto_published_at` metadata | Schema migration |
| B.4 | Archive/retract API + dashboard | API + web |
| B.5 | Ranking visibility policy (hide vs label pending) | Dashboard + API filter |
| B.6 | Update E2E: auto-publish path + supervisor reject flow | Tests |
| B.7 | Staged rollout: dev → staging auto-publish → prod | Ops |

**Rollback:** Re-enable Model A flag; archive auto-published reports if needed.

### Phase C — Model C (if approved later)

| Step | Action | Dependency |
|------|--------|------------|
| C.1 | Complete Phase B delivery | Required baseline |
| C.2 | Automated quality gates (min agent coverage, score thresholds, budget) | New rules engine |
| C.3 | Auto-hold publication when gates fail | Orchestrator or report service |
| C.4 | Disable approval UI requirement for prod roles | RBAC review |

**Rollback:** Harder — requires data and comms if bad reports were published externally.

---

## 8. Implementation estimate

Estimates assume one engineer familiar with the codebase; no orchestration redesign.

| Work package | Model A (recommended) | Model B (full) | Model C (safe) |
|--------------|----------------------|----------------|----------------|
| Policy / docs / runbook | **0.5 day** | 1 day | 1 day |
| Config-only toggle to B/C | — | **0.5 day** (not recommended alone) | 0.5 day |
| Publication alerts | 1–2 days (optional) | **2–3 days** | 2–3 days |
| Auto-publish flag + audit fields | — | **3–5 days** | 3–5 days |
| Archive/retract + dashboard | — | **3–5 days** | 3–5 days |
| Ranking visibility policy | — | **2–3 days** | 2–3 days |
| Quality auto-gates | — | — | **5–10 days** |
| E2E + regression | — | **2–3 days** | 3–5 days |
| **Total** | **0.5–3 days** (optional alerts) | **~2–3 sprints** | **~3–5 sprints** |

**Model A path to production:** **0 code days** if decision is accepted as-is; **1–2 days** for pending-approval alert only.

---

## 9. Risk analysis

### 9.1 Risk register (production)

| ID | Risk | Model A | Model B (toggle only) | Model B (full) | Model C |
|----|------|---------|------------------------|----------------|---------|
| R1 | Publish unreviewed bad recommendation | Low | **High** | Medium | **High** |
| R2 | Founder SLA miss / stale summary | Medium | Low | Low | Low |
| R3 | Misread pipeline success vs publication | Medium | Medium | Low | Medium |
| R4 | Ranking visible before “approval” | Medium | Medium | Low–Med | Medium |
| R5 | No rollback of published report | Low | **High** | Low | **High** |
| R6 | Audit / compliance trace | Low | **High** | Low | **High** |
| R7 | PR score “autonomy” misleading | Low (document) | Low | Low | Medium |

### 9.2 Production-readiness implications

| PR theme | Model A | Model B | Model C |
|----------|---------|---------|---------|
| Autonomous pipeline execution | ✅ | ✅ | ✅ |
| Autonomous **publication** | ❌ (intentional) | ✅ | ✅ |
| Governance / founder fit | ✅ | ⚠️ | ❌ |
| Observability fit | ✅ (pending-approval gap) | Needs publication alerts | Needs quality metrics |
| Dashboard + E2E | ✅ | Partial retest | Retest + new gates |
| Legal / “advice” exposure | Lower | Higher | Highest |

**Conclusion:** Model A maximizes **production readiness under the current product definition**. Models B/C improve the autonomy **score** only if the product definition changes to accept publication risk or invest in compensating controls.

---

## 10. Approval record (to complete)

| Field | Value |
|-------|--------|
| Recommended model | **Model A — Human-in-the-loop** |
| Production `REQUIRE_FOUNDER_APPROVAL` | **Keep `true`** (pending your approval) |
| Code changes in #13 | **None** |
| Next remediation if Model A | Optional: pending-approval alert (#14) |
| Next remediation if Model B | New epic per Phase B above |

**Approver:** ___________________  
**Date:** ___________________  
**Notes:** ___________________

---

## 11. References (code reviewed, unchanged)

| Area | Path |
|------|------|
| Approval service | `api/app/services/approval.py` |
| Venture reports | `api/app/reports/venture/service.py` |
| Executive ranking | `api/app/ranking/service.py` |
| Pipeline stages 13–14 | `api/app/pipeline/executor.py` |
| Dashboard summary | `api/app/services/dashboard.py` |
| Config | `api/app/config.py` |
| Dashboard UI | `web/src/app/(founder)/approvals/page.tsx`, `approval-actions.tsx` |
| Tests | `api/tests/approval/`, `web/e2e/approvals-mutations.spec.ts` |

---

## 12. Related documentation

- [autonomy-policy-review.md](./autonomy-policy-review.md) — detailed checkpoint map (#9)
- [vision.md](./vision.md) — human-in-the-loop principle
- [operations.md](./operations.md) — approval runbook
- [pipeline-orchestration.md](./pipeline-orchestration.md) — stages 13–14
