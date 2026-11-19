#!/usr/bin/env bash
set -Eeuo pipefail

EMAIL="spinlnw10@gmail.com"
APP_DIR="/opt/ck-nexus-gmail"
TOKEN_DIR="$APP_DIR/credentials"

echo "=================================================="
echo " CK-NEXUS :: GMAIL_LOGIN"
echo " Account : $EMAIL"
echo " Mode    : Google OAuth 2.0"
echo "=================================================="

# --------------------------------------------------
# 1. Safety checks
# --------------------------------------------------
if [[ $EUID -ne 0 ]]; then
  echo "ERROR: run as root"
  exit 1
fi

mkdir -p "$TOKEN_DIR"
chmod 700 "$APP_DIR" "$TOKEN_DIR"

# --------------------------------------------------
# 2. Install Google Cloud CLI if missing
# --------------------------------------------------
if ! command -v gcloud >/dev/null 2>&1; then
  echo "[1/5] Installing Google Cloud CLI..."

  apt-get update -y
  apt-get install -y ca-certificates curl gnupg apt-transport-https

  install -m 0755 -d /etc/apt/keyrings

  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | gpg --dearmor -o /etc/apt/keyrings/cloud.google.gpg

  chmod a+r /etc/apt/keyrings/cloud.google.gpg

  echo \
  "deb [signed-by=/etc/apt/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" \
    > /etc/apt/sources.list.d/google-cloud-sdk.list

  apt-get update -y
  apt-get install -y google-cloud-cli
else
  echo "[1/5] Google Cloud CLI: FOUND"
fi

echo
echo "[2/5] Starting Google OAuth..."
echo
echo "IMPORTANT:"
echo "  Google account : $EMAIL"
echo "  Do NOT enter your Gmail password into this script."
echo "  Google will authenticate you directly."
echo

# --------------------------------------------------
# 3. OAuth
# --------------------------------------------------
gcloud auth application-default login \
  --no-launch-browser \
  --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/gmail.modify"

# --------------------------------------------------
# 4. Locate ADC credentials
# --------------------------------------------------
ADC="${GOOGLE_APPLICATION_CREDENTIALS:-}"

if [[ -z "$ADC" ]]; then
  ADC="$HOME/.config/gcloud/application_default_credentials.json"
fi

if [[ ! -f "$ADC" ]]; then
  echo
  echo "ERROR: OAuth credentials were not created."
  exit 2
fi

cp "$ADC" "$TOKEN_DIR/application_default_credentials.json"
chmod 600 "$TOKEN_DIR/application_default_credentials.json"

# --------------------------------------------------
# 5. Test Gmail API
# --------------------------------------------------
echo
echo "[3/5] Getting OAuth access token..."

TOKEN="$(gcloud auth application-default print-access-token \
  --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/gmail.modify" 2>/dev/null || true)"

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: Could not obtain OAuth access token."
  exit 3
fi

echo "[4/5] Testing Gmail API..."

PROFILE="$(
  curl -fsS \
    -H "Authorization: Bearer $TOKEN" \
    "https://gmail.googleapis.com/gmail/v1/users/me/profile"
)"

API_EMAIL="$(python3 -c '
import json,sys
d=json.load(sys.stdin)
print(d.get("emailAddress",""))
' <<<"$PROFILE")"

if [[ "$API_EMAIL" != "$EMAIL" ]]; then
  echo
  echo "ERROR: Google account mismatch."
  echo "Expected : $EMAIL"
  echo "Received : ${API_EMAIL:-UNKNOWN}"
  exit 4
fi

echo
echo "[5/5] GMAIL LOGIN VERIFIED"
echo "----------------------------------------"
echo "Account : $API_EMAIL"
echo "Gmail API: OK"
echo "OAuth   : OK"
echo "Token   : $TOKEN_DIR/application_default_credentials.json"
echo "----------------------------------------"
echo
echo "STATUS=GMAIL_OAUTH_CONNECTED"
echo "ACCOUNT=$API_EMAIL"
echo "GMAIL_API=OK"
echo
