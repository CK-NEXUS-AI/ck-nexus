#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${1:-/etc/cknexus/cknexus-p0.env}"
case "$ENV_FILE" in
  /etc/cknexus/cknexus-p0.env) ENV_PROFILE=system ;;
  "$ROOT/.env.prod") ENV_PROFILE=repo ;;
  *) echo "Blocked: ENV_FILE must be /etc/cknexus/cknexus-p0.env or $ROOT/.env.prod" >&2; exit 2 ;;
esac
if [[ ! -f "$ENV_FILE" || -L "$ENV_FILE" ]]; then
  echo "Blocked: approved environment file is missing or a symlink" >&2
  exit 2
fi
export CKNEXUS_COMPOSE_FILE="$ROOT/docker-compose.p0.yml"
export CKNEXUS_ENV_FILE="$ENV_FILE"
set -a
source "$ENV_FILE"
set +a
exec python3 "$ROOT/runbooks/p0_runbook_v3.py" --env-profile "$ENV_PROFILE" "${@:2}"
