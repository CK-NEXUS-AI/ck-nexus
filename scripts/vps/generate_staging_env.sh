#!/usr/bin/env bash
set -euo pipefail
OUT="${1:-/etc/cknexus/cknexus-p0.env}"
if [[ -e "$OUT" ]]; then echo "Refusing to overwrite $OUT" >&2; exit 1; fi
install -d -m 700 "$(dirname "$OUT")"
secret(){ openssl rand -hex "$1"; }
cat > "$OUT" <<EOF
COMPOSE_PROJECT_NAME=cknexus-p0
CKNEXUS_ENVIRONMENT=staging
POSTGRES_IMAGE=postgres:16-alpine
N8N_IMAGE=n8nio/n8n:2.32.6
REDIS_IMAGE=redis:7-alpine
CKNEXUS_DB_PASSWORD=$(secret 24)
N8N_DB_PASSWORD=$(secret 24)
N8N_ENCRYPTION_KEY=$(secret 32)
CKNEXUS_ACCESS_TOKEN=$(secret 32)
CKNEXUS_EMAIL_WEBHOOK_TOKEN=$(secret 32)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-luna
CKNEXUS_EMAIL_LEASE_SECONDS=300
CKNEXUS_PORT=8000
N8N_PORT=5678
N8N_HOST=localhost
N8N_PROTOCOL=http
N8N_WEBHOOK_URL=http://127.0.0.1:5678/
TZ=Asia/Bangkok
CKNEXUS_EVIDENCE_ROOT=/var/tmp/cknexus-evidence
CKNEXUS_SOURCE_COMMIT=
EOF
chmod 600 "$OUT"
echo "Created $OUT (mode 600). Fill OPENAI_API_KEY and CKNEXUS_SOURCE_COMMIT before full P0 closeout."
