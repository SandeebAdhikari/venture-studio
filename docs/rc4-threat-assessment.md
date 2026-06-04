# V2 RC4 — Threat assessment (API authorization)

Companion to [rc4-security-report.md](./rc4-security-report.md). STRIDE-oriented view of the **current** implementation.

## Assets

| Asset | Location | Sensitivity |
|-------|----------|-------------|
| Shared `API_KEY` | API settings, BFF `API_KEY` env | **Critical** — full API impersonation |
| `OPENAI_API_KEY` | API worker env | **Critical** — spend + data exfil via prompts |
| PostgreSQL / Redis | Backend | **Critical** — all venture data, queue, heartbeats |
| Dashboard sessions | `dashboard_session` cookie | **High** — BFF-proxied API access |
| `DASHBOARD_USERS` credentials | Web env | **High** — role-bearing login |
| Venture reports / rankings | DB | **High** — business decisions |
| Prometheus `/metrics` | Public on API port | **Low–medium** — reconnaissance |

## Threat actors

| Actor | Capability | Primary path |
|-------|------------|--------------|
| Anonymous internet | Scan, probe health/metrics | Unauthenticated endpoints if API exposed |
| Stolen BFF session | Role-limited via RBAC | Cookie theft (XSS, physical, malware) |
| Stolen `API_KEY` | **Full API** | Leaked env, logs, CI artifact, backup, insider |
| Malicious insider (admin) | Approve, run pipeline, read data | BFF as admin or API key |
| Malicious insider (viewer) | Read via BFF only | Unless they obtain `API_KEY` |
| Compromised worker/BFF host | Read secrets, call API locally | Supply chain / container escape |

---

## Attack surface matrix

| Surface | AuthN | AuthZ | Exposure if misconfigured |
|---------|-------|-------|---------------------------|
| `GET /health`, `/health/ready` | None | N/A | Low — DoS only |
| `GET /metrics` | None | N/A | Medium — version/load signals |
| `/api/v1/*` (protected) | `X-API-Key` | None (binary) | **Critical** if port public |
| Next.js `/api/v1/*` BFF | Session JWT | RBAC | High — bounded by role |
| Next.js pages | Session | Page RBAC | Medium |
| `POST /api/auth/login` | Password | Rate limit **external** | Credential guessing |

---

## STRIDE per critical flow

### Direct API call with leaked key

| Category | Analysis |
|----------|----------|
| **Spoofing** | Attacker presents valid `X-API-Key` — indistinguishable from legitimate automation |
| **Tampering** | All P0/P1/P2 mutations available (delete sources, publish reports, run pipeline) |
| **Repudiation** | No per-caller identity in API audit logs |
| **Information disclosure** | All GET endpoints readable |
| **Denial of service** | Enqueue many pipeline/jobs; exhaust LLM budget; fill Redis queue |
| **Elevation of privilege** | N/A at API — already maximum |

**Likelihood:** Medium (secret leakage is common). **Impact:** Critical. **Risk:** **High**.

### BFF bypass (call FastAPI directly)

| Category | Analysis |
|----------|----------|
| **Spoofing** | Requires `API_KEY`, not session |
| **Elevation** | Viewer or guest with key → founder-level API access |

**Likelihood:** Medium if API port reachable. **Impact:** Critical. **Risk:** **High** without network controls.

### Admin session abuse

| Category | Analysis |
|----------|----------|
| **Tampering** | Approve/reject ventures, trigger pipeline — by design for trusted admin |
| **Elevation** | Cannot delete sources via BFF; **can** if same person obtains `API_KEY` |

**Likelihood:** Low (trusted role). **Impact:** High (wrong approval). **Risk:** **Medium** (process + key hygiene).

### Session hijack (founder)

| Category | Analysis |
|----------|----------|
| **Spoofing** | Full BFF access including platform mutations |
| **Tampering** | Equivalent to founder using UI |

**Likelihood:** Low with httpOnly + TLS. **Impact:** Critical. **Risk:** **Medium**.

### API key brute force

| Category | Analysis |
|----------|----------|
| **Spoofing** | Guess 32+ char key |

**Likelihood:** Very low at key strength; higher if short/dev keys in prod. **Mitigation:** production_validation exit 15. **Risk:** **Low** if constraints enforced.

### Metrics scraping

| Category | Analysis |
|----------|----------|
| **Information disclosure** | Pipeline counters, alert metrics |

**Likelihood:** High if `/metrics` on public IP. **Impact:** Low–medium. **Risk:** **Medium** without network restriction.

---

## Privilege escalation paths

| # | Path | Preconditions | Result |
|---|------|---------------|--------|
| 1 | **API key acquisition** | Any leak of `API_KEY` | Full founder-equivalent API access; bypasses all BFF roles |
| 2 | **BFF → API trust** | Compromise Next server env | Attacker inherits key from server (not browser) |
| 3 | **Role misconfiguration** | `DASHBOARD_USERS` JSON grants `founder` to wrong user | Full BFF + effective full API via proxy |
| 4 | **Viewer + API key** | Viewer creds **and** separate key leak | Read-only UI but full API mutation |
| 5 | **Admin approval power** | Valid admin session | Publication decisions without founder (policy, not API bug) |
| 6 | **Autonomy flag** | `REQUIRE_FOUNDER_APPROVAL=false` | Auto-publish without human gate (config escalation) |

No in-app path elevates **viewer → founder** without a secret or config change.

---

## Residual risk summary

| Risk ID | Description | Severity | Model A | Model B | Model C |
|---------|-------------|----------|---------|---------|---------|
| R1 | Single API key = full access | Critical | Mitigate (network) | Unacceptable | Unacceptable |
| R2 | No API-layer RBAC | High | Accept | Fix Tier 2 | Fix V3 |
| R3 | Unauthenticated `/metrics` | Medium | Mitigate (network) | Mitigate | Fix + auth |
| R4 | No per-user API audit | Medium | Accept | Improve | Required |
| R5 | Admin can approve | Medium | Process | Process + scoped keys | Policy engine |
| R6 | LLM spend via `/jobs/*` | High | Network + key hygiene | Scoped automation key | Per-tenant quotas |

---

## Recommended threat priorities (no auth redesign)

1. **Eliminate public API exposure** (addresses R1, R2, R3 for Model A).
2. **Rotate `API_KEY` after any BFF/env compromise** (R1, R2).
3. **Operational separation:** automation key vs break-glass human key (Tier 2 — separate secrets, same code path initially).
4. **Founder-only approval policy** for production (R5, R6 business impact).

See [rc4-authorization-recommendations.md](./rc4-authorization-recommendations.md) for implementation phasing.
