#!/usr/bin/env bash
set -u

CRED="/etc/cknexus/creds/openai_api_key.cred"
REPO="/opt/actions-runner/_work/ck-nexus/ck-nexus"

echo "=== CK-NEXUS Q11 FINAL CHECK ==="

echo "[1] CREDENTIAL"
stat -c 'owner=%U:%G mode=%a size=%s' "$CRED"

echo
echo "[2] LOADCREDENTIAL + REAL Q11"

TMP="$(mktemp)"
chmod 600 "$TMP"

systemd-run --quiet --wait --pipe --collect \
  --property=User=root \
  --property="LoadCredential=openai_api_key:$CRED" \
  /bin/bash -c '
    export OPENAI_API_KEY="$(cat "$CREDENTIALS_DIRECTORY/openai_api_key")"
    cd "'"$REPO"'"
    /root/.local/bin/uv run python scripts/test_openai_live.py
  ' >"$TMP" 2>&1

RC=$?

echo
echo "[3] SAFE RESULT"

if grep -q 'CK-NEXUS-P0-SMOKE-PASS' "$TMP"; then
    echo "Q11_SENTINEL=OBSERVED"
else
    echo "Q11_SENTINEL=NOT_OBSERVED"
fi

if grep -q 'P0-AI-001 PASS' "$TMP"; then
    echo "Q11_RESULT=PASS"
else
    echo "Q11_RESULT=NOT_PASS"
fi

echo "PROCESS_EXIT=$RC"

echo
echo "[4] SAFE PROVIDER CLASSIFICATION"

grep -E \
'RateLimitError|AuthenticationError|PermissionDeniedError|BadRequestError|APIConnectionError|ModuleNotFoundError|P0-AI-001 (PASS|FAIL|BLOCKED)' \
"$TMP" 2>/dev/null | head -20 || true

rm -f "$TMP"

echo
if [ "$RC" -eq 0 ]; then
    echo "Q11_FINAL=EXECUTED_SUCCESS"
else
    echo "Q11_FINAL=FAILED_OR_BLOCKED"
fi
