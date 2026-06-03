# E2E production impact assessment — Remediation #10

## Implementation review

| Component | Status | Notes |
|-----------|--------|-------|
| Playwright suite | Complete | `web/e2e/*.spec.ts`, `web/playwright.config.ts` |
| CI workflow | Complete | `.github/workflows/web-e2e.yml` on `push` + `pull_request` to `main` |
| Deterministic fixtures | Complete | `api/scripts/seed_e2e_fixtures.py` + `web/e2e/fixtures/seed.ts` |
| Approval mutations | Complete | `web/e2e/approvals-mutations.spec.ts` (serial) |
| Pipeline visibility | Complete | `web/e2e/pipeline-visibility.spec.ts` + seed pipeline run |
| Report visibility | Complete | Draft assertion before approve; published after approve |

### Seed script behavior

`api/scripts/seed_e2e_fixtures.py` (idempotent via `e2e_marker` in `pipeline_runs.config_snapshot`):

1. Creates opportunity with mocked agent outputs (no LLM).
2. Generates two executive ranking runs and two draft venture reports with pending approvals.
3. Inserts a completed pipeline run with COLLECT + VENTURE_REPORT stages for dashboard visibility.

Requires `REQUIRE_FOUNDER_APPROVAL=true`.

### Reliability controls

| Control | Setting |
|---------|---------|
| CI retries | `retries: 2` in `playwright.config.ts` |
| CI workers | `workers: 1` |
| Serial mutations | `test.describe.configure({ mode: "serial" })` |
| CI parallel | `fullyParallel: false` when `CI=true` |
| Locators | Role/label based; BFF response waits |
| No snapshots | Text/role assertions only |

---

## CI verification

Workflow: `.github/workflows/web-e2e.yml`

| Step | Validates |
|------|-----------|
| `docker compose up --build -d` | API + worker + postgres + redis |
| `verify-deployment.sh` | Migrations + `/health/ready` |
| `seed_e2e_fixtures.py` | Approval + pipeline fixtures |
| `npm run build` + `npm run start` | Production-mode Next.js |
| `npm run test:e2e:ci` | Full Playwright suite |

**Triggers:** `push` to `main`, `pull_request` targeting `main`.

**On failure:** `playwright-report` artifact uploaded (7-day retention).

---

## E2E coverage summary

| Flow | Spec | Confidence |
|------|------|------------|
| Page loads (6 routes) | `pages.spec.ts` | High |
| Sidebar navigation | `workflows.spec.ts` | High |
| Reports library / markdown | `workflows.spec.ts` | Medium (skips if empty) |
| Opportunities table | `workflows.spec.ts` | High |
| Approvals list / filter / detail | `workflows.spec.ts` | High |
| Pipeline run history | `workflows.spec.ts` | High |
| Viewer RBAC | `viewer.spec.ts` | High |
| Draft report visibility | `approvals-mutations.spec.ts` | High |
| Approve → publish | `approvals-mutations.spec.ts` | High |
| Reject ranking | `approvals-mutations.spec.ts` | High |
| Request research | `approvals-mutations.spec.ts` | High |
| Seeded pipeline run visible | `pipeline-visibility.spec.ts` | High |

**Total tests:** 19 (16 founder project + 3 viewer)

### Uncovered flows

- `/agents` page load
- Admin-role E2E project
- Logout / session expiry
- Mobile viewport / nav drawer
- BFF/API error UX
- Full live `run_pipeline` execution (14 stages, LLM)
- Web production Docker image in CI
- Direct FastAPI access bypassing BFF

### Production confidence level

| Dimension | Level | Rationale |
|-----------|-------|-----------|
| Dashboard auth + routing | **High** | Covered by pages, viewer, navigation |
| Approval publication path | **High** | Approve/reject/research + draft/published |
| Pipeline monitoring UI | **Medium–High** | Seeded run visible; not full orchestrator run |
| Nightly automation | **Medium** | Backend E2E does not run full scheduled pipeline |
| Regression on merge | **High** (once committed + pushed) | CI blocks PR/push to `main` |

**Overall E2E production confidence: High** for founder dashboard critical paths, contingent on `web-e2e.yml` and `web/e2e/**` being tracked in git and passing on GitHub.

---

## Production readiness impact

| Before #10 | After #10 |
|------------|-----------|
| E2E existed locally only | E2E committed + CI gate |
| Approval mutations untested | Approve / reject / research covered |
| Report publish path unverified in UI | Draft → published validated |
| Pipeline UI only empty-state safe | Seeded completed run asserted |
| Remote CI score penalty | E2E guaranteed on `main` PRs |

**Estimated production readiness score impact:** +4 to +6 points (from ~74 toward ~78–80) once changes are merged and CI green.

**Remaining E2E gaps for 90+:** full pipeline smoke, web Docker image, admin project, agents page, failure-mode UX.

---

## Related documentation

- [e2e-testing.md](./e2e-testing.md) — runbook
- [ci.md](./ci.md) — workflow matrix
- [dashboard-auth.md](./dashboard-auth.md) — session model for E2E credentials
