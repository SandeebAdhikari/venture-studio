#!/bin/sh
set -eu

log() {
  printf '[entrypoint] %s\n' "$*"
}

run_bootstrap() {
  mode="$1"
  log "Running bootstrap (mode=${mode})"
  python -m app.deployment.bootstrap --mode "${mode}" --alembic-cwd /app
}

case "${1:-}" in
  arq)
    run_bootstrap worker
    log "Starting worker: $*"
    exec "$@"
    ;;
  uvicorn)
    run_bootstrap api
    log "Starting API: $*"
    exec "$@"
    ;;
  *)
    log "Unknown command '${1:-}'; expected arq or uvicorn"
    exit 1
    ;;
esac
