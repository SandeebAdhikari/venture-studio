# API authorization — production approach

Current implementation (`api/app/api/deps.py`): single shared secret via `X-API-Key`, compared with `secrets.compare_digest`.

## Current model (V2)

| Layer | Auth | Notes |
|-------|------|-------|
| Direct API (`/api/v1/*`) | Shared `API_KEY` | All protected routes use same privilege |
| Dashboard BFF (`web` → API) | Session JWT + RBAC | Founder/admin/viewer; API key server-side only |
| Approval mutations | BFF RBAC | Not API-key scoped per user |

**Production validation** rejects weak or example keys when `ENVIRONMENT=production` (`deployment/production_validation.py`).

## Gaps before public API exposure

| Gap | Risk |
|-----|------|
| No per-route or per-role API keys | Key leak = full API access |
| No per-user audit on API calls | Only dashboard sessions are user-scoped |
| No rate limiting in app | Abuse / brute force at edge |

## Recommended production posture (minimal — no architecture redesign)

### Tier 1 — Ship now (configuration + edge)

1. **Do not expose** `/api/v1` to the public internet; bind API to private network or VPC.
2. Dashboard-only operators use **BFF + JWT**; rotate `API_KEY` only on server/BFF.
3. Generate `API_KEY` with 32+ random bytes; store in secret manager.
4. Terminate TLS at load balancer; optional IP allowlist for API port.
5. Keep `ENVIRONMENT=production` (disables OpenAPI UI — `main.py`).

### Tier 2 — Minimal code (future sprint, if public API required)

| Change | Effort | Benefit |
|--------|--------|---------|
| `API_KEYS` JSON map `{ "key": "role" }` + role checks on sensitive routers | ~2–3 days | Read-only vs admin keys |
| Optional `X-Request-Id` + structured audit log on mutations | ~1 day | Traceability |
| Reverse-proxy rate limit (nginx/Cloudflare) | Ops | Brute-force mitigation |

**Not required for founder-only private deploy** if Tier 1 is satisfied.

## V3 is out of scope

OAuth, per-tenant RBAC on API, and fine-grained policy engines are deferred. V2 stabilization uses Tier 1 + production key validation.

## Verification

- `verify_api_key` uses constant-time compare (`secrets.compare_digest`)
- Production bootstrap rejects `change-me-*` and CI example keys
