#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${1:-/etc/cknexus/cknexus-p0.env}"
export CKNEXUS_COMPOSE_FILE="$ROOT/docker-compose.p0.yml"
export CKNEXUS_ENV_FILE="$ENV_FILE"
set -a; source "$ENV_FILE"; set +a
exec python3 "$ROOT/runbooks/p0_runbook_v3.py" --env-file "$ENV_FILE" "${@:2}"
