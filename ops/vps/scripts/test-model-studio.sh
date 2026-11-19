#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="https://ws-ql6g7mayu0p09o4y.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
MODEL="${MODEL:-qwen3-coder}"

echo "=========================================="
echo " Alibaba Cloud Model Studio API Test"
echo "=========================================="
echo "Endpoint: ${BASE_URL}"
echo "Model:    ${MODEL}"
echo

read -rsp "Enter NEW API Key: " DASHSCOPE_API_KEY
echo

if [[ -z "${DASHSCOPE_API_KEY}" ]]; then
  echo "[ERROR] API Key is empty."
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'unset DASHSCOPE_API_KEY; rm -rf "$TMP_DIR"' EXIT

echo
echo "[1/2] Checking API authentication..."

STATUS="$(
  curl -sS \
    --connect-timeout 10 \
    --max-time 30 \
    -o "${TMP_DIR}/models.json" \
    -w '%{http_code}' \
    "${BASE_URL}/models" \
    -H "Authorization: Bearer ${DASHSCOPE_API_KEY}"
)"

echo "HTTP_STATUS: ${STATUS}"
python3 -m json.tool "${TMP_DIR}/models.json" 2>/dev/null \
  | head -n 60 || cat "${TMP_DIR}/models.json"
echo

if [[ "${STATUS}" != "200" ]]; then
  echo "[FAILED] Authentication/model-list request failed."
  echo "Check API Key, Workspace, region, and API error."
  exit 1
fi

echo
echo "[2/2] Testing chat completion..."

STATUS="$(
  curl -sS \
    --connect-timeout 10 \
    --max-time 90 \
    -o "${TMP_DIR}/chat.json" \
    -w '%{http_code}' \
    "${BASE_URL}/chat/completions" \
    -H "Authorization: Bearer ${DASHSCOPE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$(MODEL_NAME="${MODEL}" python3 -c '
import json, os
print(json.dumps({
    "model": os.environ["MODEL_NAME"],
    "messages": [
        {
            "role": "user",
            "content": "Reply with exactly: API connection test successful"
        }
    ],
    "stream": False
}))
')"
)"

echo "HTTP_STATUS: ${STATUS}"
python3 -m json.tool "${TMP_DIR}/chat.json" 2>/dev/null \
  || cat "${TMP_DIR}/chat.json"
echo

if [[ "${STATUS}" == "200" ]]; then
  echo "[SUCCESS] Model Studio API and chat completion passed."
else
  echo "[FAILED] Chat completion failed."
  echo "Check model availability, permissions, and API error."
  exit 1
fi
