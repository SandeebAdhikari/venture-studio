# V2 RC4 — Authorization implementation recommendations

Analysis-only sprint. **Does not redesign authentication** (`verify_api_key` + `X-API-Key` remain). Focus: minimum acceptable security, deployment constraints, future RBAC roadmap.

## Minimum acceptable security by deployment model

### Model A — Trusted internal API (V2 RC target)

**Acceptable when all are true:**

| # | Control | Owner |
|---|---------|-------|
| 1 | API listens only on private network / internal LB | Infra |
| 2 | `ENVIRONMENT=production` + strong `API_KEY` (validation exit 15) | Config |
| 3 | Dashboard is the only human path; BFF RBAC enabled | Web deploy |
| 4 | `API_KEY` not in client JS, git, or CI logs | Engineering |
| 5 | `REQUIRE_FOUNDER_APPROVAL=true` unless founder accepts Model B | Product |
| 6 | `/metrics` scraped from internal network only | Infra |
| 7 | Edge rate limit on dashboard login and (optional) API | Infra |

**Audit mapping:** API Authorization **FAIL** at code level, **PASS** at system level with constraints documented.

### Model B — Multi-user internal platform

Add to Model A:

| # | Control | Effort |
|---|---------|--------|
| 8 | Separate secrets: `API_KEY_AUTOMATION` vs `API_KEY_ADMIN` (Tier 2a) | Config + small code |
| 9 | API-layer role dependency on P0 routers | Tier 2b (~2–3 days) |
| 10 | Structured audit log: `principal`, `route`, `mutation` on POST/PATCH/DELETE | Tier 2c (~1 day) |
| 11 | Disable or rotate viewer accounts; no API key issued to viewers | Process |

### Model C — Public SaaS

**Not recommended on V2 codebase.** Minimum would include OAuth2/OIDC, tenant isolation, per-user API tokens with scopes, rate limiting, WAF, SOC2-style audit — see §Future RBAC roadmap (V3+).

---

## Production deployment constraints (checklist)

Copy into release runbooks ([production-deployment-runbook.md](./production-deployment-runbook.md) cross-link).

- [ ] Security group / firewall: **deny** `0.0.0.0/0` → API `:8000`
- [ ] Allow API from: BFF subnet, worker, CI deploy runner (break-glass)
- [ ] `API_KEY` from secret manager; rotation calendar
- [ ] Web: `AUTH_SECRET`, `DASHBOARD_USERS` with `passwordHash` only
- [ ] Verify `canProxyApi` tests pass (`web` vitest) after role changes
- [ ] Smoke: viewer cannot `POST /api/v1/approvals/...` via BFF (403)
- [ ] Smoke: unauthenticated BFF returns 401
- [ ] Confirm CORS not `*` in production (`app/main.py`)
- [ ] Confirm `/docs` disabled in production
- [ ] Document who holds founder vs admin accounts

---

## Tier 2 — Minimal code (future sprint, preserves auth mechanism)

Keeps `verify_api_key`; adds **authorization** after authentication.

### Phase 2a — Multiple keys, same compare pattern (~1 day)

```text
API_KEYS='{"<automation-secret>":"automation","<admin-secret>":"admin","<readonly-secret>":"readonly"}'
```

- Extend `deps.py`: resolve key → `ApiPrincipal(role=...)`
- Reject unknown keys with same 401
- Default single `API_KEY` maps to `admin` or `founder` for backward compatibility

### Phase 2b — Router-level role requirements (~2 days)

| Role | Allow |
|------|-------|
| `readonly` | All GET under protected_router |
| `automation` | GET + `pipeline`, `jobs`, `scheduler`, agent `POST .../run`, collection triggers |
| `admin` | automation + `approvals`, `reports` publish, `executive-*` |
| `founder` | all including `sources`, `rss-feeds`, `categories`, `complaints` DELETE |

Implementation sketch (no redesign):

- `require_roles(*roles)` dependency using principal from 2a
- Apply to `APIRouter` includes or per-route on P0/P2 modules

Align prefixes with `web/src/lib/auth/rbac.ts` to avoid BFF/API policy drift.

### Phase 2c — Audit envelope (~1 day)

On mutating requests, log JSON: `request_id`, `principal_role`, `method`, `path`, `status_code` (no body secrets).

Optional: accept `X-Actor-Username` from BFF **only** if mTLS between BFF and API (trust boundary).

---

## Future RBAC roadmap (V3+)

| Phase | Capability | Enables |
|-------|------------|---------|
| V3.1 | OAuth2 / OIDC for dashboard; API tokens issued per user | Model B with SSO |
| V3.2 | Resource-scoped permissions (e.g. opportunity_id) | Delegation |
| V3.3 | Tenant_id on all rows + request context | Model C multi-tenant |
| V3.4 | Policy engine (OPA/Cedar) or managed IAM | Enterprise SaaS |
| V3.5 | Per-tenant rate limits + API abuse alerts | Public API |

**Explicitly deferred:** Replacing `X-API-Key` with JWT on FastAPI for V2 — would be a redesign.

---

## BFF ↔ API alignment recommendations

| Issue | Recommendation |
|-------|----------------|
| API does not know BFF user | BFF sends optional `X-Actor-Username` after session verify (Tier 2c); API logs only |
| Admin can approve but not delete sources at BFF | Document; optional API `admin` role matches BFF |
| Viewer blocked from GET `/approvals` at BFF | Intentional; API key still exposes — network constraint |
| Agent POST paths not in `ADMIN_MUTATE_PREFIXES` | Admin cannot trigger agents via UI; founder only — **good**; API key still can |

No BFF change required for Model A.

---

## What not to do in RC4

- Do not add OAuth to FastAPI in this sprint
- Do not split routers without a key→role map (auth without authz repeat)
- Do not expose `/api/v1` publicly “temporarily”
- Do not issue `API_KEY` to viewer-role humans

---

## Verification (existing)

| Check | Command / location |
|-------|-------------------|
| API key required | `api/tests/test_api.py` — `test_sources_require_api_key` |
| Constant-time compare | `api/app/api/deps.py` — `secrets.compare_digest` |
| Production weak key | `api/tests/deployment/test_production_validation.py` |
| BFF RBAC | `web/src/lib/auth/rbac.test.ts`, `bff-guard.test.ts` |

**Suggested RC4 manual tests (ops):**

1. From laptop without VPN: API port unreachable.
2. With key: `curl -H "X-API-Key: …" POST .../pipeline/run` succeeds on internal network.
3. Viewer login: BFF `POST .../approvals/.../approve` → 403.
4. Missing key: 401 on protected route.

---

## Document index

| Report | Path |
|--------|------|
| Security report | [rc4-security-report.md](./rc4-security-report.md) |
| Threat assessment | [rc4-threat-assessment.md](./rc4-threat-assessment.md) |
| This file | `rc4-authorization-recommendations.md` |
