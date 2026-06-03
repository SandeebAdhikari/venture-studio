# Dashboard authentication and authorization

The founder dashboard (`web/`) uses **BFF-layer session auth** before proxying to FastAPI. Direct API clients continue to use `X-API-Key` unchanged.

## Approach

| Layer | Mechanism |
|-------|-----------|
| Session | Signed JWT (`HS256`) in httpOnly cookie `dashboard_session` via [`jose`](https://github.com/panva/jose) |
| Users | `DASHBOARD_USERS` JSON env (plaintext `password` for dev; `passwordHash` for production) |
| Page guard | Next.js [`middleware.ts`](../web/src/middleware.ts) — redirect to `/login` |
| API guard | BFF [`authorizeBffRequest`](../web/src/lib/auth/bff-guard.ts) + middleware on `/api/v1/*` |
| Passwords | Node `scrypt` (`web/src/lib/auth/password.ts`) |

## Roles

| Role | Pages | BFF API |
|------|-------|---------|
| **founder** | All protected routes | All methods/paths |
| **admin** | Dashboard, opportunities, reports, budget, pipeline, approvals, agents | GET on viewer + admin read prefixes; POST/PATCH/DELETE on operational prefixes (`approvals/`, `pipeline/`, `scheduler/`, `jobs/`, `executive-ranking/`) — not platform admin (`sources`, `rss-feeds`, `categories`, `complaints`) |
| **viewer** | Dashboard, opportunities, reports, budget | GET/HEAD only on `dashboard`, `budget`, `reports`, `opportunities`, `executive-reports` |

Protected pages: `/dashboard`, `/pipeline`, `/approvals`, `/reports`, `/budget`, `/agents`, `/opportunities`.

## Environment variables

```bash
# Required (web/.env.local or deployment secrets)
AUTH_SECRET=<32+ char random string>
DASHBOARD_USERS=[{"username":"founder","passwordHash":"scrypt:...","role":"founder"}, ...]
API_KEY=<unchanged — injected only after BFF auth>

# Optional
SESSION_MAX_AGE_SECONDS=28800
```

Generate password hash (Node REPL):

```javascript
const { hashPassword } = require("./web/dist/..."); // or use app login once in dev
```

For local dev, plaintext `password` in `DASHBOARD_USERS` is hashed at load time (see `web/.env.example`).

## Login flow

1. User submits credentials at `/login` → `POST /api/auth/login`
2. Server validates against `DASHBOARD_USERS`, sets httpOnly cookie
3. Client calls `/api/v1/*` with `credentials: "include"`
4. BFF verifies session + RBAC, then adds `X-API-Key` to upstream FastAPI request
5. `POST /api/auth/logout` clears the cookie

## Files

- `web/src/middleware.ts` — route protection
- `web/src/lib/auth/*` — users, session, RBAC, BFF guard
- `web/src/app/api/auth/*` — login, logout, session
- `web/src/app/login/page.tsx` — login UI
- `web/src/app/api/v1/[...path]/route.ts` — guarded proxy

See [security-impact-auth.md](./security-impact-auth.md) for threat model and residual risks.
