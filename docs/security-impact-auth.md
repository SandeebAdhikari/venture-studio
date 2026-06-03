# Security impact assessment — dashboard BFF auth

## Problem addressed

Previously, any browser client could call `/api/v1/*` on the Next.js BFF without a dashboard identity. The BFF injected `X-API-Key` for every request, effectively exposing privileged backend operations to unauthenticated users who could reach the web app.

## Changes

- Session JWT in **httpOnly** cookie (not accessible to JS on the page)
- **Middleware** blocks unauthenticated access to dashboard pages and BFF routes
- **RBAC** enforces role-specific page access and HTTP method rules on the BFF proxy
- `X-API-Key` is only attached **after** session verification and RBAC checks

## Threat model (residual)

| Risk | Mitigation | Residual |
|------|------------|----------|
| Stolen session cookie | httpOnly, `Secure` in production, `SameSite=Lax`, 8h default TTL | XSS on dashboard origin could still exfiltrate via CSRF if combined with other bugs; keep dependencies patched |
| Credential brute force | Deploy behind rate limiting / WAF (not in app scope) | Add reverse-proxy limits in production |
| Shared `API_KEY` | Still required for BFF→API; not sent to browser | Compromise of Next server env still yields API access |
| Direct FastAPI access | Unchanged API key auth | Network policy should restrict API port to BFF/trusted clients |
| Weak `AUTH_SECRET` / passwords | Document minimum secret length; prefer `passwordHash` in prod | Operator responsibility |
| Role misconfiguration | Env JSON validated at login load | Wrong `DASHBOARD_USERS` grants excess privilege until redeploy |

## What is not changed

- FastAPI `verify_api_key` for direct API consumers
- Business logic in `api/`
- Public health/metrics endpoints

## Verification

- Vitest: `web/src/lib/auth/*.test.ts` (session, RBAC, users, BFF guard)
- Manual: unauthenticated `/api/v1/dashboard/summary` → 401; viewer POST approvals → 403

## Rollout checklist

1. Set `AUTH_SECRET` and `DASHBOARD_USERS` in production secrets (remove plaintext passwords)
2. Rotate `API_KEY` if it was ever exposed via the old public BFF
3. Confirm reverse proxy does not cache authenticated BFF responses
4. Smoke-test all three roles against protected pages and approval mutations
