# Founder Dashboard

The founder dashboard is a Next.js 15 application in `web/` that provides operational visibility and approval actions for the Venture Studio.

For technical architecture details, see also [dashboard-architecture.md](./dashboard-architecture.md).

---

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS v4 |
| Components | shadcn-style (Radix UI primitives) |
| Data fetching | SWR with polling |
| Auth | BFF proxy injects `X-API-Key` server-side |

The dashboard contains **no business logic**. All scoring, ranking, budget thresholds, and approval decisions are computed by the FastAPI backend.

---

## Pages

| Route | Purpose | Primary APIs |
|-------|---------|--------------|
| `/dashboard` | Overview metrics, top opportunities, job/scheduler summary | `GET /dashboard/summary`, `GET /dashboard/opportunities?top_n=5` |
| `/opportunities` | Full opportunity inventory with ranking scores | `GET /dashboard/opportunities`, `GET /opportunities` |
| `/pipeline` | Pipeline run history and stage timeline | `GET /dashboard/pipeline?include_stages=true` |
| `/reports` | Venture and executive reports with markdown viewer | `GET /dashboard/reports`, `GET /reports/{id}/markdown` |
| `/approvals` | Founder approve/reject/research actions | `GET /approvals`, `POST /approvals/{id}/{action}` |
| `/budget` | Daily LLM spend, warnings, history chart | `GET /budget`, `GET /budget/history` |
| `/agents` | Agent activity and coverage summary | `GET /dashboard/summary` (agents section) |

Root `/` redirects to `/dashboard`.

---

## BFF Proxy

Client components call relative URLs like `/api/v1/dashboard/summary`. The catch-all route at `web/src/app/api/v1/[...path]/route.ts` forwards requests to the FastAPI backend with the server-side `API_KEY` header.

```
Browser → /api/v1/* (Next.js) → http://API_URL/api/v1/* (FastAPI)
```

Environment variables:

| Variable | Description |
|----------|-------------|
| `API_URL` | Backend URL (default `http://localhost:8000`) |
| `API_KEY` | Same value as backend `API_KEY` |

---

## Polling Intervals

No WebSocket or SSE. SWR `refreshInterval`:

| Page | Interval |
|------|----------|
| Pipeline | 10s |
| Dashboard, Approvals | 15s |
| Opportunities, Agents | 20s |
| Reports, Budget | 30s |

---

## Local Development

```bash
# Terminal 1: backend infrastructure
docker compose up -d postgres redis

# Terminal 2: API
cd api && uvicorn app.main:app --reload --port 8000

# Terminal 3: worker
cd api && arq app.workers.worker.WorkerSettings

# Terminal 4: dashboard
cd web
cp .env.local.example .env.local   # if present; else create with API_URL + API_KEY
npm install
npm run dev
```

Open http://localhost:3000

---

## Production Build

```bash
cd web
npm run build
npm start
```

The dashboard is **not** included in `docker-compose.yml`. Deploy separately (Vercel, container, or same VPS as API).

---

## Project Structure

```
web/src/
├── app/
│   ├── (founder)/           # Layout with sidebar navigation
│   │   ├── dashboard/page.tsx
│   │   ├── opportunities/page.tsx
│   │   ├── pipeline/page.tsx
│   │   ├── reports/page.tsx
│   │   ├── approvals/page.tsx
│   │   ├── budget/page.tsx
│   │   └── agents/page.tsx
│   ├── api/v1/[...path]/    # BFF proxy
│   ├── layout.tsx
│   └── page.tsx             # Redirect to /dashboard
├── components/
│   ├── layout/              # Sidebar, page header
│   ├── ui/                  # Button, Card, Badge, etc.
│   ├── shared/              # DataTable, MetricCard
│   ├── approvals/           # Approval action buttons
│   ├── pipeline/            # Stage timeline
│   ├── budget/              # Usage widgets
│   ├── agents/              # Agent grid
│   └── reports/             # Markdown viewer
├── hooks/use-api.ts         # SWR wrappers
├── lib/api/                 # client.ts, server.ts
└── types/api.ts             # Backend type mirrors
```

---

## Type Safety

`src/types/api.ts` manually mirrors Pydantic response schemas. Update when backend schemas change. OpenAPI codegen is not configured.

---

## Related Documentation

- [dashboard-architecture.md](./dashboard-architecture.md) — detailed design principles
- [api-overview.md](./api-overview.md) — backend API reference
- [deployment.md](./deployment.md) — deployment instructions
