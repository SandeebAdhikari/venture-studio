# Web Deployment Strategy

How to deploy the Next.js founder dashboard (`web/`) and how it fits CI/CD.

---

## Recommendation

**Use a separate deployment for the frontend** — not bundled into the API Docker image.

| Approach | Recommended for | Why |
|----------|-----------------|-----|
| **Vercel / managed Next.js** | Solo founder, fastest path | Zero-config App Router, env secrets for BFF, global CDN, preview URLs per PR |
| **Web Docker container** | Single VPS / Kubernetes | Same ops model as API; full control; use `web/Dockerfile` |
| **API monolith container** | Not recommended | Couples release cycles; wastes resources; Next.js and Python scale differently |

### Primary recommendation: Vercel (or equivalent)

The dashboard is a **BFF presentation layer**. It only needs:

- `API_URL` — internal or public backend URL (server-side)
- `API_KEY` — server-side only (never `NEXT_PUBLIC_`)

Vercel aligns with the existing architecture in [deployment.md](./deployment.md):

```
Vercel (web/)  ──BFF──►  VPS/containers (api/ + worker)
```

**Benefits**

- Automatic HTTPS and CDN for static assets
- Preview deployments on every PR (pair with `web-quality.yml` + `web-deployment-check.yml`)
- No Node process to manage on the API host
- Independent rollbacks when backend and frontend diverge

**Trade-offs**

- Second platform to configure (env vars, domain)
- Serverless cold starts (minimal for this dashboard)

### Alternative: Web Docker container

Use when you want **one platform** (Docker Compose, Fly.io, Railway, ECS).

The repo includes [`web/Dockerfile`](../web/Dockerfile) with Next.js **standalone** output:

```bash
docker build -t ai-venture-studio-web ./web
docker run -d \
  -p 3000:3000 \
  -e API_URL=http://api:8000 \
  -e API_KEY="$API_KEY" \
  ai-venture-studio-web
```

**Benefits**

- Unified container workflow with API/worker
- CI validates the image in `web-deployment-check.yml`
- Works offline / air-gapped environments

**Trade-offs**

- You manage TLS, scaling, and Node runtime
- Static asset CDN is DIY (nginx, CloudFront, etc.)

### Not recommended: Single combined image

Do **not** add Next.js build steps to `api/Dockerfile`. The API image should remain Python-only for:

- Smaller images and faster deploys
- Independent scaling (API replicas ≠ dashboard replicas)
- Clear security boundary (API keys in BFF only)

---

## Docker Compose today

[`docker-compose.yml`](../docker-compose.yml) runs **postgres, redis, api, worker** — not `web`.

| Service | In Compose | Rationale |
|---------|------------|-----------|
| postgres, redis | Yes | Shared infrastructure |
| api, worker | Yes | Same Python image, different commands |
| web | No | Deploy separately (Vercel) or add optionally (see below) |

### Optional: add web to Compose (local full stack)

For local “everything in Docker” testing, add:

```yaml
  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      API_URL: http://api:8000
      API_KEY: ${API_KEY}
    depends_on:
      api:
        condition: service_healthy
```

This is **optional** for development convenience, not required for production.

---

## CI/CD gates (merge blocking)

Frontend must pass before merge:

| Workflow | Job | Fails on |
|----------|-----|----------|
| [`web-quality.yml`](../.github/workflows/web-quality.yml) | Typecheck, lint, unit tests | TS errors, ESLint errors, test failures |
| [`web-deployment-check.yml`](../.github/workflows/web-deployment-check.yml) | Build + verify + Docker | `next build` failure, missing routes/artifacts, Docker build/start failure |

### What build verification checks

[`web/scripts/verify-build.mjs`](../web/scripts/verify-build.mjs) asserts after `next build`:

- Dashboard pages: `/dashboard`, `/opportunities`, `/pipeline`, `/reports`, `/approvals`, `/budget`, `/agents`
- BFF API route: `/api/v1/[...path]`
- Server bundles for dashboard page and API route handler
- shadcn/ui components compile transitively through page builds (no separate step — build failure catches broken UI)

Run locally:

```bash
cd web
npm ci
npm run validate   # typecheck + lint + test + build + verify-build
```

---

## Branch protection (recommended)

Require these status checks on `main`:

**Backend (existing)**

- Quality / Ruff lint and format
- Test / Migration validation
- Test / Pytest
- Deployment Check / Build validation

**Frontend (new)**

- Web Quality / Typecheck, lint, and unit tests
- Web Deployment Check / Next.js build verification
- Web Deployment Check / Web Docker image

---

## Environment variables (production)

| Variable | Required | Notes |
|----------|----------|-------|
| `API_URL` | Yes | Backend base URL (server-only) |
| `API_KEY` | Yes | Matches backend `API_KEY`; never expose to browser |

CI sets `API_KEY=ci-github-actions-api-key` for builds. Production values come from the hosting platform secret store.

---

## Related documentation

- [ci.md](./ci.md) — all GitHub Actions workflows
- [deployment.md](./deployment.md) — full stack deployment
- [dashboard.md](./dashboard.md) — dashboard features
- [web/README.md](../web/README.md) — local development
