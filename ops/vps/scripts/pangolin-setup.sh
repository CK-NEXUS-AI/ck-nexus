#!/usr/bin/env bash
set +e

CONFIG_DIR="$HOME/.config/pangolinfo"
CONFIG_FILE="$CONFIG_DIR/api-key"
OUT="$HOME/pangolin-setup-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$CONFIG_DIR" "$OUT"

echo "=========================================="
echo " PANGOLINFO API KEY SETUP"
echo "=========================================="
echo ""
echo "📌 ขั้นตอนที่ 1: ไปรับ Permanent API Key"
echo ""
echo "   1. เปิดเบราว์เซอร์ไปที่:"
echo "      https://tool.pangolinfo.com/#/en/menu/dataAPI/keys"
echo ""
echo "   2. Login (หรือสมัครฟรี)"
echo "   3. ไปที่ Account Center → Profile → API Key"
echo "   4. คัดลอก Permanent Key (ไม่ใช่ Short-term Token)"
echo ""
echo "   ⚠ Permanent Key ไม่หมดอายุ — Short-term หมดอายุใน 7/14 วัน"
echo ""

# --- ถามหา API Key ---
read -r -p "🔑 วาง API Key ที่นี่ (จะไม่แสดงบนหน้าจอ): " -s API_KEY
echo ""
echo ""

if [ -z "$API_KEY" ]; then
  echo "❌ ไม่มี API Key — ยกเลิก"
  exit 1
fi

# --- ตรวจรูปแบบเบื้องต้น ---
echo "==> ตรวจรูปแบบ Key"
if [ ${#API_KEY} -lt 10 ]; then
  echo "  ⚠ Key สั้นเกินไป (${#API_KEY} ตัวอักษร) — อาจไม่ถูกต้อง"
else
  echo "  ✓ ความยาว: ${#API_KEY} ตัวอักษร"
  echo "  ✓ ขึ้นต้น: ${API_KEY:0:4}****"
fi

# --- บันทึกอย่างปลอดภัย ---
echo ""
echo "==> บันทึก Key"
printf '%s' "$API_KEY" > "$CONFIG_FILE"
chmod 600 "$CONFIG_FILE"
chmod 700 "$CONFIG_DIR"

echo "  📁 ที่เก็บ: $CONFIG_FILE"
echo "  🔒 สิทธิ์  : $(stat -c %A "$CONFIG_FILE")"

# --- ทดสอบเรียก API ---
echo ""
echo "==> ทดสอบเรียก API"
echo ""

RESP=$(curl -s -o "$OUT/test-response.json" -w "%{http_code}" \
  --max-time 20 \
  -X POST "https://scrapeapi.pangolinfo.com/api/v1/auth" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{}' 2>&1)

echo "  HTTP Status: $RESP"
echo ""
echo "  Response (ตัด 500 ตัวอักษรแรก):"
head -c 500 "$OUT/test-response.json" 2>/dev/null | sed 's/^/    /'
echo ""

# --- สรุป ---
{
  echo "=========================================="
  echo " PANGOLINFO SETUP SUMMARY"
  echo "=========================================="
  echo ""
  echo "Date          : $(date -u)"
  echo "Config file   : $CONFIG_FILE"
  echo "Key length    : ${#API_KEY}"
  echo "Key prefix    : ${API_KEY:0:4}****"
  echo "HTTP status   : $RESP"
  echo ""
  case "$RESP" in
    200|201)
      echo "✅ API Key ใช้งานได้"
      ;;
    401|403)
      echo "❌ API Key ไม่ถูกต้อง หรือหมดอายุ"
      ;;
    000)
      echo "⚠ เชื่อมต่อไม่ได้ (network/DNS)"
      ;;
    *)
      echo "⚠ Status ไม่คาดคิด — ตรวจ response"
      ;;
  esac
  echo ""
  echo "=========================================="
} | tee "$OUT/SUMMARY.txt"

cd "$OUT" && sha256sum *.txt *.json 2>/dev/null | tee SHA256SUMS.txt

echo ""
echo "=========================================="
echo " เสร็จแล้ว"
echo "=========================================="
echo ""
echo "📌 วิธีใช้ Key ต่อ:"
echo ""
echo "  # อ่าน key จาก config"
echo "  export PANGOLIN_API_KEY=\$(cat $CONFIG_FILE)"
echo ""
echo "  # เรียก API"
echo "  curl -X POST https://scrapeapi.pangolinfo.com/api/v1/scrape \\"
echo "    -H \"Authorization: Bearer \$PANGOLIN_API_KEY\" \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"url\":\"https://www.amazon.com/dp/B0B4NLGCH5\"}'"
echo ""
echo "  # ใน Python"
echo "  from pangolinfo_mcp import PangolinfoMCPClient"
echo "  client = PangolinfoMCPClient(api_key=open('$CONFIG_FILE').read())"
echo ""
echo "=========================================="
