# AI Venture Studio — Founder Dashboard

Production-grade Next.js dashboard for founder review and studio monitoring. **All business logic lives in the FastAPI backend**; this app is a typed presentation layer.

## Stack

- **Next.js 15** (App Router)
- **TypeScript**
- **Tailwind CSS v4**
- **shadcn-style UI** (Radix + CVA primitives)
- **SWR** for polling-based real-time updates

## Quick start

```bash
# Terminal 1 — backend
docker compose up -d postgres redis
cd api && alembic upgrade head && uvicorn app.main:app --reload

# Terminal 2 — dashboard
cd web
cp .env.example .env.local   # set API_URL and API_KEY
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) → redirects to `/dashboard`.

## Environment

| Variable | Description |
|----------|-------------|
| `API_URL` | FastAPI base URL (server-only, e.g. `http://localhost:8000`) |
| `API_KEY` | Matches backend `API_KEY` — **never** exposed to the browser |

The browser calls `/api/v1/*` on the Next.js server, which proxies to FastAPI with `X-API-Key`.

## Pages

| Route | Backend APIs consumed |
|-------|----------------------|
| `/dashboard` | `GET /dashboard/summary`, `GET /dashboard/opportunities` |
| `/opportunities` | `GET /dashboard/opportunities`, `GET /opportunities` |
| `/pipeline` | `GET /dashboard/pipeline` |
| `/reports` | `GET /dashboard/reports`, `GET /reports/{id}/markdown` |
| `/approvals` | `GET /approvals`, `POST /approvals/{id}/approve\|reject\|research` |
| `/budget` | `GET /budget`, `GET /budget/history` |
| `/agents` | `GET /dashboard/summary` (agents section) |

## Architecture

See [docs/dashboard.md](../docs/dashboard.md) and [docs/dashboard-architecture.md](../docs/dashboard-architecture.md).

## Scripts

```bash
npm run dev      # development server
npm run build    # production build
npm run start    # production server
npm run lint     # ESLint
```
