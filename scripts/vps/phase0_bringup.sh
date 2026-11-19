#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${1:-/etc/cknexus/cknexus-p0.env}"
COMPOSE="$ROOT/docker-compose.p0.yml"
EVIDENCE_ROOT="${CKNEXUS_EVIDENCE_ROOT:-/var/tmp/cknexus-evidence}"
RUN_ID="p0-phase0-$(date +%Y%m%d-%H%M%S)"
OUT="$EVIDENCE_ROOT/$RUN_ID"
mkdir -p "$OUT/logs" "$OUT/artifacts"
if [[ ! -f "$ENV_FILE" ]]; then echo "Missing env file: $ENV_FILE" >&2; exit 2; fi
if [[ "$(stat -c '%a' "$ENV_FILE")" != "600" ]]; then echo "Env file must be mode 600." >&2; exit 1; fi
set -a; source "$ENV_FILE"; set +a
if [[ "${CKNEXUS_ENVIRONMENT:-}" != "staging" ]]; then echo "Refusing: CKNEXUS_ENVIRONMENT must be staging" >&2; exit 2; fi
if grep -Eq 'replace-with|^CKNEXUS_DB_PASSWORD=$|^CKNEXUS_ACCESS_TOKEN=$|^CKNEXUS_EMAIL_WEBHOOK_TOKEN=$' "$ENV_FILE"; then
  echo "Placeholder/empty required secret detected." >&2; exit 2
fi
{
  echo "run_id=$RUN_ID"
  echo "started_at=$(date -Iseconds)"
  echo "hostname=$(hostname)"
  echo "kernel=$(uname -a)"
  echo "docker=$(docker --version)"
  echo "compose=$(docker compose version)"
  echo "source_commit=${CKNEXUS_SOURCE_COMMIT:-UNBOUND}"
  echo "source_tree_sha256=$(cd "$ROOT" && find . -type f ! -path './.git/*' ! -path './evidence/*' -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
} > "$OUT/manifest.txt"

docker compose --env-file "$ENV_FILE" -f "$COMPOSE" config > "$OUT/artifacts/compose.resolved.yml"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE" pull db migrate 2>&1 | tee "$OUT/logs/pull.log"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE" up -d --build db migrate app 2>&1 | tee "$OUT/logs/up.log"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE" ps > "$OUT/artifacts/compose-ps.txt"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE" logs --no-color --tail=500 > "$OUT/logs/compose.log"

for i in $(seq 1 90); do curl -fsS "http://127.0.0.1:${CKNEXUS_PORT:-8000}/health" > "$OUT/artifacts/health.json" && break; sleep 2; done
curl -fsS "http://127.0.0.1:${CKNEXUS_PORT:-8000}/health" >/dev/null

docker compose --env-file "$ENV_FILE" -f "$COMPOSE" exec -T db psql -U cknexus -d cknexus -Atc "SELECT to_regclass('public.email_journal'), to_regclass('public.email_outbox'), to_regclass('public.email_audit_logs'), to_regclass('public.creator_runs');" > "$OUT/artifacts/schema.txt"
if grep -qE '^$' "$OUT/artifacts/schema.txt"; then echo "Schema verification failed" >&2; exit 1; fi

docker compose --env-file "$ENV_FILE" -f "$COMPOSE" exec -T db postgres --version > "$OUT/artifacts/postgres-version.txt"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE" exec -T app python --version > "$OUT/artifacts/python-version.txt" 2>&1

docker image inspect "${POSTGRES_IMAGE:-postgres:16-alpine}" --format '{{json .RepoDigests}}' > "$OUT/artifacts/postgres-image-digests.json" || true
(cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
echo "P0 Phase 0 bring-up: PASS"
echo "Evidence: $OUT"
