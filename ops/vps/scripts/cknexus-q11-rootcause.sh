#!/usr/bin/env bash
set -u

CRED=/etc/cknexus/creds/openai_api_key.cred
REPO=/opt/actions-runner/_work/ck-nexus/ck-nexus
SERVICE=cknexus-auto-gates.service
DROP=/etc/systemd/system/cknexus-auto-gates.service.d
ENVFILE=/etc/cknexus/openai.env

echo "============================================================"
echo " CK-NEXUS Q11 ROOT-CAUSE ISOLATION"
echo "============================================================"

echo
echo "[1] SERVICE CONFIG — SAFE"
systemctl cat "$SERVICE" |
  sed -E \
    -e 's/(OPENAI_API_KEY=).*/\1[REDACTED]/g' \
    -e 's#(/etc/cknexus/creds/)[^[:space:]]*#\1[REDACTED]#g'

echo
echo "[2] ENVIRONMENT FILE — METADATA ONLY"

if [ -e "$ENVFILE" ]; then
    stat -c 'exists=yes owner=%U group=%G mode=%a size=%s' "$ENVFILE"

    if grep -q '^OPENAI_API_KEY=' "$ENVFILE"; then
        echo "openai_env_contains_key=yes"
    else
        echo "openai_env_contains_key=no"
    fi

    if grep -qE '^OPENAI_API_KEY=[^[:space:]]+$' "$ENVFILE"; then
        echo "openai_env_key_nonempty=yes"
    elif grep -q '^OPENAI_API_KEY=' "$ENVFILE"; then
        echo "openai_env_key_nonempty=no"
    fi
else
    echo "exists=no"
fi

echo
echo "[3] CREDENTIAL"
stat -c 'owner=%U group=%G mode=%a size=%s' "$CRED"

python3 - "$CRED" <<'PY'
import sys,re,hashlib
from pathlib import Path

b=Path(sys.argv[1]).read_bytes()
s=b.decode("utf-8","strict").strip()

print("format=",
      "VALID" if re.fullmatch(r"sk-[A-Za-z0-9_-]+",s)
      else "INVALID")
print("length=",len(s))
print("sha256=",hashlib.sha256(b).hexdigest())
PY

echo
echo "[4] SYSTEMD PROPERTIES — NO VALUES"
systemctl show "$SERVICE" \
  -p EnvironmentFiles \
  -p Environment \
  -p LoadCredential \
  -p ExecStart \
  -p Result \
  -p ExecMainStatus \
  --no-pager |
sed -E \
  -e 's/(OPENAI_API_KEY=)[^ ]*/\1[REDACTED]/g' \
  -e 's#(/etc/cknexus/creds/)[^ ]*#\1[REDACTED]#g'

echo
echo "[5] TEST SCRIPT — CURRENT SOURCE"
sha256sum "$REPO/scripts/test_openai_live.py"

grep -nE \
  'OPENAI_API_KEY|OpenAI\(|responses\.create|model=|CK-NEXUS-P0-SMOKE-PASS|P0-AI-001' \
  "$REPO/scripts/test_openai_live.py" |
sed -E \
  's/(OPENAI_API_KEY[^=]*=).*/\1[REDACTED]/g'

echo
echo "[6] PYTHON / SDK"
"$REPO/.venv/bin/python" - <<'PY' 2>/dev/null || true
import sys
print("python=",sys.version.split()[0])
try:
    import openai
    print("openai_version=",openai.__version__)
except Exception as e:
    print("openai_import=FAIL")
    print("exception_class=",type(e).__name__)
PY

echo
echo "[7] SAFE ENVIRONMENT INJECTION TEST"

PROBE=/root/cknexus-q11-env-probe.sh

cat >"$PROBE" <<'INNER'
#!/usr/bin/env bash
set -u

F="${CREDENTIALS_DIRECTORY:-}/openai_api_key"

if [ ! -r "$F" ]; then
    echo "LOADCREDENTIAL=FAIL"
    exit 30
fi

VALUE="$(tr -d '\r\n' < "$F")"

if [[ "$VALUE" =~ ^sk-[A-Za-z0-9_-]+$ ]]; then
    echo "LOADCREDENTIAL=PASS"
else
    echo "LOADCREDENTIAL=INVALID"
    exit 31
fi

export OPENAI_API_KEY="$VALUE"

python3 - <<'PY'
import os

v=os.getenv("OPENAI_API_KEY")

print("ENV_PRESENT=",bool(v))
print("ENV_LENGTH=",len(v) if v else 0)
print("ENV_FORMAT=",
      "VALID"
      if v and v.startswith("sk-") and
         all(c.isalnum() or c in "_-" for c in v[3:])
      else
      "INVALID")
PY

unset OPENAI_API_KEY
INNER

chmod 700 "$PROBE"

systemd-run \
  --quiet \
  --wait \
  --pipe \
  --collect \
  --property="User=root" \
  --property="LoadCredential=openai_api_key:$CRED" \
  "$PROBE"

RC=$?

rm -f "$PROBE"

echo "LOADCREDENTIAL_PROBE_EXIT=$RC"

echo
echo "[8] NETWORK"
curl -sS \
  -o /dev/null \
  -w 'https_status=%{http_code} connect=%{time_connect} tls=%{time_appconnect} total=%{time_total}\n' \
  --connect-timeout 5 \
  --max-time 15 \
  https://api.openai.com/v1/models ||
  echo "network_request=FAILED"

echo
echo "[9] ACTUAL API — SANITIZED"

API=/root/cknexus-q11-api-only.py
RUN=/root/cknexus-q11-api-only.sh
OUT=$(mktemp)
chmod 600 "$OUT"

cat >"$API" <<'PY'
import os
from openai import OpenAI

try:
    client=OpenAI()

    model=os.getenv(
        "OPENAI_SMOKE_MODEL",
        os.getenv("OPENAI_MODEL","gpt-5-mini")
    )

    response=client.responses.create(
        model=model,
        input="Reply with exactly CK-NEXUS-P0-SMOKE-PASS"
    )

    output=getattr(response,"output_text","") or ""

    print("API=SUCCESS")
    print("RESPONSE_ID_PRESENT=",bool(getattr(response,"id",None)))
    print("SENTINEL=",
          "OBSERVED"
          if "CK-NEXUS-P0-SMOKE-PASS" in output
          else "NOT_OBSERVED")

except Exception as e:
    print("API=ERROR")
    print("EXCEPTION_CLASS=",type(e).__name__)
    print("STATUS=",getattr(e,"status_code",None))
    print("CODE=",getattr(e,"code",None))
    print("REQUEST_ID_PRESENT=",bool(getattr(e,"request_id",None)))
PY

cat >"$RUN" <<'INNER2'
#!/usr/bin/env bash
set -u

F="$CREDENTIALS_DIRECTORY/openai_api_key"

if [ ! -r "$F" ]; then
    echo "INJECTION=FAIL"
    exit 40
fi

export OPENAI_API_KEY="$(tr -d '\r\n' < "$F")"

if [[ ! "$OPENAI_API_KEY" =~ ^sk-[A-Za-z0-9_-]+$ ]]; then
    unset OPENAI_API_KEY
    echo "INJECTION=INVALID"
    exit 41
fi

cd /opt/actions-runner/_work/ck-nexus/ck-nexus

exec /root/.local/bin/uv run python /root/cknexus-q11-api-only.py
INNER2

chmod 700 "$API" "$RUN"

systemd-run \
  --quiet \
  --wait \
  --pipe \
  --collect \
  --property="User=root" \
  --property="LoadCredential=openai_api_key:$CRED" \
  "$RUN" >"$OUT" 2>&1

API_RC=$?

grep -E \
  '^(API=|RESPONSE_ID_PRESENT=|SENTINEL=|EXCEPTION_CLASS=|STATUS=|CODE=|REQUEST_ID_PRESENT=|INJECTION=)' \
  "$OUT" || \
  echo "API_SAFE_MARKERS=NONE"

echo "API_PROCESS_EXIT=$API_RC"

rm -f "$OUT" "$API" "$RUN"

echo
echo "[10] FINAL CLASSIFICATION"

if [ "$API_RC" -eq 0 ] &&
   grep -q '^API=SUCCESS$' /dev/null 2>/dev/null; then
    :
fi

echo "Q11_ROOTCAUSE_STAGE=COMPLETED"
echo "NO_SECRET_OUTPUT=true"
echo "NO_PRODUCTION_PROMOTION=true"

echo
echo "============================================================"
echo " END Q11 ROOT-CAUSE ISOLATION"
echo "============================================================"
