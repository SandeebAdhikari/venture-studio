# End-to-end testing (Playwright)

Production-grade Playwright tests validate authenticated founder dashboard flows against a **live FastAPI backend** (Docker Compose). Tests avoid visual snapshots; assertions use roles, headings, and BFF response readiness.

## Quick start (local)

### 1. Backend

```bash
# From repository root
cp .env.example .env
echo 'REQUIRE_FOUNDER_APPROVAL=true' >> .env   # if not already set
# Ensure API_KEY matches web env below
docker compose up -d
./api/scripts/verify-deployment.sh
cd api && PYTHONPATH=. REQUIRE_FOUNDER_APPROVAL=true python scripts/seed_e2e_fixtures.py
```

### 2. Dashboard env

Create `web/.env.local`:

```bash
API_URL=http://localhost:8000
API_KEY=<same as .env API_KEY>
AUTH_SECRET=local-e2e-auth-secret-at-least-32-characters
DASHBOARD_USERS=[{"username":"founder","password":"e2e-test-password","role":"founder"},{"username":"viewer","password":"e2e-test-password","role":"viewer"}]
```

### 3. Run tests

```bash
cd web
npm ci
npm run build
npm run start   # or npm run dev on :3000
E2E_API_KEY=<your-api-key> npm run test:e2e
```

## Scripts

| Script | Purpose |
|--------|---------|
| `npm run test:e2e` | Run all Playwright projects |
| `npm run test:e2e:ci` | CI reporter (`line` + GitHub) |
| `npm run test:e2e:ui` | Interactive Playwright UI |

## Authentication in E2E

1. **Global setup** signs in as `founder` → `e2e/.auth/founder.json` (gitignored).
2. **Founder specs** reuse `storageState`.
3. **Viewer specs** log in per test via `loginViaUi(page, "viewer")`.

| Variable | Default | Role |
|----------|---------|------|
| `E2E_PASSWORD` | `e2e-test-password` | Founder |
| `E2E_VIEWER_PASSWORD` | `e2e-test-password` | Viewer |
| `E2E_BASE_URL` | `http://localhost:3000` | Dashboard URL |
| `E2E_API_KEY` | `API_KEY` | Seed script |

## CI integration (first-class gate)

Workflow: [`.github/workflows/web-e2e.yml`](../.github/workflows/web-e2e.yml)

Runs on **every push to `main`** and **every pull request** targeting `main`.

1. Docker Compose (postgres, redis, api, worker) with `REQUIRE_FOUNDER_APPROVAL=true`
2. `verify-deployment.sh`
3. `seed_e2e_fixtures.py`
4. `npm run build` + `npm run start`
5. `npm run test:e2e:ci` (retries: 2, workers: 1)

See [e2e-production-impact.md](./e2e-production-impact.md) for coverage and readiness impact.

## Test inventory (19 tests)

| Spec | Tests | Focus |
|------|-------|-------|
| `pages.spec.ts` | 6 | Authenticated page loads |
| `workflows.spec.ts` | 5 | Navigation, reports, opportunities, approvals list, pipeline |
| `approvals-mutations.spec.ts` | 4 | Draft visibility, approve, reject, request research (serial) |
| `pipeline-visibility.spec.ts` | 1 | Seeded completed run in history |
| `viewer.spec.ts` | 3 | Viewer RBAC |

## Covered workflows

- All six required dashboard pages (live BFF)
- Sidebar navigation
- Report library and markdown viewer
- Approvals: filter, detail, **approve → publish**, **reject**, **request research**
- Report **draft** and **published** visibility
- Pipeline run history with **completed** seeded run
- Viewer read-only and redirect from `/pipeline`

## Remaining gaps

- `/agents` page
- Admin E2E project
- Logout / session expiry
- Full 14-stage live pipeline (LLM)
- Web Docker image in CI
- Mobile viewport

## Flake avoidance

- Wait for `GET /api/v1/...` before UI assertions
- Role/label locators only
- CI: `retries: 2`, `workers: 1`, `fullyParallel: false`
- Serial approval mutations
- Idempotent DB seed (`e2e_playwright_seed_v1` marker)

## Layout

```
web/
  playwright.config.ts
  e2e/
    global-setup.ts
    pages.spec.ts
    workflows.spec.ts
    approvals-mutations.spec.ts
    pipeline-visibility.spec.ts
    viewer.spec.ts
    fixtures/
      auth.ts
      page-ready.ts
      seed.ts
api/scripts/
  seed_e2e_fixtures.py
```

## Related docs

- [e2e-production-impact.md](./e2e-production-impact.md)
- [dashboard-auth.md](./dashboard-auth.md)
- [ci.md](./ci.md)
