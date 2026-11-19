#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${CKNEXUS_BASE_URL:-http://127.0.0.1:8000}"
TOKEN="${CKNEXUS_ACCESS_TOKEN:-}"
AUTH=()
if [ -n "$TOKEN" ]; then AUTH=(-H "Authorization: Bearer $TOKEN"); fi
curl -fsS -X POST "${BASE_URL}/api/integrations/github/test" "${AUTH[@]}"
printf '\n'
