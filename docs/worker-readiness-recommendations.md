# Worker readiness recommendations

## Current behavior

| Check | Default | Endpoint |
|-------|---------|----------|
| `WORKER_READINESS_REQUIRED` | `false` | `GET /health/ready` → `worker` status `ok` with detail `not required` |
| Heartbeat source | Redis keys `observability:worker:{id}` | TTL `WORKER_HEARTBEAT_TTL_SEC` (90 s) |
| Worker offline alert | `ALERT_WORKER_MONITOR_ENABLED` | API monitor when **no** heartbeats |

## Production recommendation

Set **`WORKER_READINESS_REQUIRED=true`** on the **API** service so:

- Load balancers and Compose `api` healthcheck fail when no worker is heartbeating
- Nightly `run_pipeline` enqueue does not succeed against an API that appears healthy but cannot process jobs

### When to keep `false`

- Local dev with API-only (no worker container)
- CI API tests without Redis worker process
- Staged rollouts where API starts before worker (use worker `start_period` and enable readiness after worker is up)

## Compose ordering

`worker` depends on `api` healthy (migrations applied). Enable `WORKER_READINESS_REQUIRED=true` **after** worker is in the same stack so `/health/ready` reflects both.

## Docker worker healthcheck (new)

The `worker` service uses:

```yaml
healthcheck:
  test: ["CMD", "python", "-m", "app.workers.healthcheck"]
```

This verifies **at least one** heartbeat in Redis (sufficient for single-worker Compose). Multi-worker deployments should ensure the probe matches your ops model (per-host process check + Redis heartbeats).

## Related

- [worker-production-impact.md](./worker-production-impact.md)
- [observability.md](./observability.md)
