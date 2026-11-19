#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export CKNEXUS_MOCK_AI="${CKNEXUS_MOCK_AI:-true}"
export CKNEXUS_EMAIL_GATEWAY_ENABLED="${CKNEXUS_EMAIL_GATEWAY_ENABLED:-true}"
export CKNEXUS_EMAIL_WEBHOOK_TOKEN="${CKNEXUS_EMAIL_WEBHOOK_TOKEN:-demo-webhook-token}"
export CKNEXUS_EMAIL_DATABASE_PATH="${CKNEXUS_EMAIL_DATABASE_PATH:-data/email-web-demo.db}"
export CKNEXUS_DATABASE_PATH="${CKNEXUS_DATABASE_PATH:-data/creator-web-demo.db}"
PORT="${PORT:-8000}"
printf '\nCK-NEXUS Full System Web Demo\n'
printf 'Open: http://127.0.0.1:%s/demo\n' "$PORT"
printf 'Demo email token: %s\n' "$CKNEXUS_EMAIL_WEBHOOK_TOKEN"
if [ -n "${GITHUB_TOKEN:-}" ]; then
  printf 'GitHub: token configured; repo=%s\n' "${GITHUB_REPO:-NOT_SET}"
else
  printf 'GitHub: not configured (set GITHUB_TOKEN and optional GITHUB_REPO)\n'
fi
printf '\n'
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
