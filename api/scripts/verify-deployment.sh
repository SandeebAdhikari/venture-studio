#!/bin/sh
# Verify a running AVS stack: migration marker in API logs and HTTP readiness.
set -eu

API_URL="${API_URL:-http://localhost:8000}"
READY_URL="${READY_URL:-${API_URL}/health/ready}"
COMPOSE_SERVICE="${COMPOSE_SERVICE:-api}"
TIMEOUT_SEC="${TIMEOUT_SEC:-120}"
MARKER="${MIGRATION_MARKER:-avs_migrations_ok}"

log() {
  printf '[verify-deployment] %s\n' "$*"
}

fail() {
  printf '[verify-deployment] ERROR: %s\n' "$*" >&2
  exit 1
}

if command -v docker >/dev/null 2>&1 && docker compose ps "${COMPOSE_SERVICE}" >/dev/null 2>&1; then
  log "Checking API logs for migration marker (${MARKER})"
  if ! docker compose logs "${COMPOSE_SERVICE}" 2>/dev/null | grep -q "${MARKER}"; then
    fail "Migration success marker not found in ${COMPOSE_SERVICE} logs"
  fi
  log "Migration marker present in logs"
else
  log "Skipping log marker check (docker compose service ${COMPOSE_SERVICE} unavailable)"
fi

log "Waiting for readiness at ${READY_URL}"
python -m app.deployment.bootstrap \
  --mode verify \
  --ready-url "${READY_URL}" \
  --timeout-sec "${TIMEOUT_SEC}"

log "Deployment verification passed"
