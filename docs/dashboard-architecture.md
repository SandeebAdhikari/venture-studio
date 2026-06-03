# Founder Dashboard Architecture

> User-facing overview: [dashboard.md](./dashboard.md)

The founder dashboard is a **Backend-for-Frontend (BFF)** Next.js application. It renders data from existing FastAPI endpoints and forwards mutations without embedding venture-studio business rules.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (founder)                        │
│  Pages: Dashboard · Opportunities · Pipeline · Reports · …    │
│  SWR polling (10–30s) · sort/filter UI · markdown viewer       │
└────────────────────────────┬────────────────────────────────────┘
                             │ fetch /api/v1/*
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Next.js (web/) — BFF layer                    │
│  app/api/v1/[...path]/route.ts  →  injects X-API-Key server-side│
│  types/api.ts                   →  mirrors backend schemas      │
│  components/                    →  presentation only              │
└────────────────────────────┬────────────────────────────────────┘
                             │ X-API-Key + /api/v1/*
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              FastAPI (api/) — source of truth                   │
│  Dashboard · Opportunities · Pipeline · Reports · Approvals     │
│  Budget · Executive ranking · Agents (via pipeline/workers)     │
└─────────────────────────────────────────────────────────────────┘
```

## Design principles

### 1. No business logic in the frontend

The dashboard **never**:

- Computes opportunity scores, rankings, or budget thresholds
- Decides approval outcomes (only POSTs founder actions to the API)
- Derives pipeline stage order (uses `stage_order` from the backend)

It **only**:

- Displays API responses
- Applies UI-level sort, filter, and search on already-fetched lists
- Polls endpoints on an interval for near-real-time updates

### 2. Credential isolation (BFF proxy)

`API_KEY` is read from server environment variables in `src/app/api/v1/[...path]/route.ts`. Client components call `/api/v1/dashboard/summary`, not `http://localhost:8000` directly. This keeps secrets off the wire to the browser.

**Dashboard auth:** Users must sign in at `/login`. The BFF verifies a session cookie and RBAC before injecting `X-API-Key`. See [dashboard-auth.md](./dashboard-auth.md).

For SSR or future server components, `src/lib/api/server.ts` offers the same pattern.

### 3. Real-time via polling (not WebSockets)

The backend exposes no WebSocket or SSE endpoints. Each page uses **SWR `refreshInterval`**:

| Page | Poll interval |
|------|---------------|
| Pipeline | 10s |
| Dashboard, Approvals | 15s |
| Opportunities, Agents | 20s |
| Reports, Budget | 30s |

A live indicator in the page header shows the active interval. Manual refresh triggers immediate revalidation.

When the backend adds push APIs, swap `usePollingApi` for subscriptions in one hook without changing page layout.

### 4. Type safety without code generation

`src/types/api.ts` mirrors Pydantic response shapes from the backend. When backend schemas change, update this file (or add OpenAPI codegen later).

### 5. Responsive layout

- **Desktop:** fixed sidebar navigation (`md:flex`)
- **Mobile:** collapsible top nav with hamburger menu
- **Tables:** horizontal scroll on narrow viewports
- **Grids:** `sm:` / `lg:` / `xl:` breakpoints for metric cards and split panels

## Project structure

```
web/src/
├── app/
│   ├── (founder)/           # Authenticated shell layout
│   │   ├── dashboard/
│   │   ├── opportunities/
│   │   ├── pipeline/
│   │   ├── reports/
│   │   ├── approvals/
│   │   ├── budget/
│   │   └── agents/
│   └── api/v1/[...path]/    # BFF proxy
├── components/
│   ├── layout/              # Sidebar, page header, app shell
│   ├── ui/                  # shadcn-style primitives
│   ├── shared/              # DataTable, MetricCard
│   ├── approvals/           # Approval action buttons
│   ├── pipeline/            # Stage timeline
│   ├── budget/              # Usage widgets
│   ├── agents/              # Agent grid
│   └── reports/             # Markdown viewer
├── hooks/use-api.ts         # SWR wrappers
├── lib/api/                 # Client + server fetch helpers
└── types/api.ts             # Backend type mirrors
```

## Page → API mapping

### Dashboard

- **`GET /dashboard/summary`** — collection, classification, research, ranking, agents, background jobs
- **`GET /dashboard/opportunities?top_n=5`** — top ranked opportunities table

### Opportunities

- **`GET /dashboard/opportunities?top_n=50`** — executive ranking view with component scores
- **`GET /opportunities?limit&offset&review_status`** — full inventory with backend filters

Client-side title filter and column sort operate on fetched rows only.

### Pipeline

- **`GET /dashboard/pipeline?limit&offset&include_stages=true`** — running run, paginated history, latest stage detail

`PipelineStages` renders `stage_runs` in backend `stage_order`.

### Reports

- **`GET /dashboard/reports?limit=20`** — venture, top-opportunity, and pipeline report lists
- **`GET /reports/{id}/markdown`** — markdown body for `ReportViewer` (react-markdown)

### Approvals

- **`GET /approvals?status&subject_type&limit&offset`** — list with filters
- **`POST /approvals/{id}/approve`** — optional `{ comment }`
- **`POST /approvals/{id}/reject`** — optional `{ comment }`
- **`POST /approvals/{id}/research`** — `{ comment }` required by backend

Comment history comes from `decisions[]` on each `ApprovalRequestRead`.

### Budget

- **`GET /budget`** — daily spend, warnings at 50/75/90%, per-agent breakdown
- **`GET /budget/history?days=30`** — daily rollup chart

### Agent Activity

- **`GET /dashboard/summary`** — reuses `agents[]` and `research.average_agent_coverage`

## Shared UI patterns

### DataTable

Generic sortable table with optional text filter. Sorting compares display values client-side; authoritative ordering for rankings remains on the backend.

### StatusBadge

Maps backend status strings to color variants (`completed` → success, `pending` → warning, etc.). Display-only heuristic — not used for decisions.

### Error and loading states

Every page uses SWR `error` + skeleton placeholders + `ErrorState` with retry. Empty lists use `EmptyState` without fabricating placeholder data.

## Deployment notes

1. Set `API_URL` to the internal FastAPI URL (e.g. `http://api:8000` in Docker Compose).
2. Set `API_KEY` to the same value as the backend.
3. Build: `cd web && npm run build && npm start`
4. Optionally add a `web` service to `docker-compose.yml` pointing at this app.

## Related documentation

- [dashboard.md](./dashboard.md) — pages and local setup
- [architecture.md](./architecture.md) — full system design
- [api-overview.md](./api-overview.md) — REST API reference
- [ci.md](./ci.md) — GitHub Actions pipelines
