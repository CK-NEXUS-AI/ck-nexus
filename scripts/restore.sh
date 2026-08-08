#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:?usage: scripts/restore.sh <backup-directory>}"
SRC="$(cd "$SRC" && pwd)"

(cd "$SRC" && sha256sum -c SHA256SUMS)

if [[ -f "$SRC/creator.sqlite3" ]]; then
  mkdir -p "$ROOT/data"
  cp -f "$SRC/creator.sqlite3" "$ROOT/data/cknexus.db"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo 'P0-BACKUP-001 BLOCKED: docker command not installed; clean boot verification cannot run'
  exit 2
fi

set -a
if [[ -f "$ROOT/.env.p0" ]]; then source "$ROOT/.env.p0"; fi
set +a

docker compose -f "$ROOT/docker-compose.p0.yml" up -d db
if [[ -f "$SRC/email-postgres.dump" ]]; then
  docker compose -f "$ROOT/docker-compose.p0.yml" exec -T db \
    pg_restore -U cknexus -d cknexus --clean --if-exists < "$SRC/email-postgres.dump"
fi

docker compose -f "$ROOT/docker-compose.p0.yml" up -d --build app
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${CKNEXUS_PORT:-8000}/health" >/tmp/ckn-p0-health.json; then
    cat /tmp/ckn-p0-health.json
    echo
    echo 'P0-BACKUP-001 RESTORE-AND-BOOT PASS'
    exit 0
  fi
  sleep 2
done

echo 'P0-BACKUP-001 FAIL: /health never became ready'
exit 1
