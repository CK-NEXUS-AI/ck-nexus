#!/usr/bin/env bash
set -Eeuo pipefail
set +x
umask 077
BASE_URL='https://xtzsfd91.rpcld.co'
API_URL="${BASE_URL}/api/v1"
SECRET_DIR='/root/.config/n8n'
SECRET_FILE="${SECRET_DIR}/api_key"
install -d -m 700 "$SECRET_DIR"
printf 'n8n API endpoint: %s\n' "$API_URL"
printf 'สร้าง API Key ใหม่ใน n8n Settings > n8n API ก่อนดำเนินการ\n'
read -rsp 'วาง n8n API Key ใหม่ (จะไม่แสดงขณะพิมพ์): ' N8N_API_KEY
printf '\n'
if [[ -z "$N8N_API_KEY" ]]; then echo '[ERROR] ไม่ได้รับ API Key'; exit 1; fi
printf '%s' "$N8N_API_KEY" > "$SECRET_FILE"
chmod 600 "$SECRET_FILE"
unset N8N_API_KEY
HTTP_CODE=$(curl -sS --connect-timeout 10 --max-time 30 \
  -H "X-N8N-API-KEY: $(cat "$SECRET_FILE")" \
  -o /tmp/n8n-api-test.json -w '%{http_code}' \
  "${API_URL}/workflows?limit=1") || { rm -f /tmp/n8n-api-test.json; echo '[ERROR] เชื่อมต่อเซิร์ฟเวอร์ไม่ได้'; exit 1; }
echo "HTTP_STATUS=${HTTP_CODE}"
case "$HTTP_CODE" in
  200) echo '[SUCCESS] n8n API authentication passed'; python3 -c 'import json; d=json.load(open("/tmp/n8n-api-test.json")); rows=d.get("data",[]) if isinstance(d,dict) else []; print("WORKFLOW_COUNT_RETURNED =",len(rows)); [print("SAMPLE_WORKFLOW_NAME =",r.get("name","(unnamed)")) for r in rows[:1]]' ;;
  401|403) echo '[ERROR] API Key ไม่ถูกต้องหรือไม่มีสิทธิ์';;
  *) echo '[ERROR] ตรวจสอบ HTTP status และการตั้งค่า n8n';;
esac
rm -f /tmp/n8n-api-test.json
