#!/bin/bash
# ═══════════════════════════════════════════════════════
# CK-NEXUS Auto Setup — ตั้งค่า Free API Keys ทั้งหมด
# ═══════════════════════════════════════════════════════
# วิธีใช้:
#   bash creator_app/credentials/scripts/auto_setup.sh
#
# ขั้นตอน:
#   1. สร้าง .env จาก .env.example
#   2. แสดง URL สมัครทุก provider ฟรี
#   3. รอ user วาง key ทีละตัว
#   4. เก็บใน vault อัตโนมัติ
#   5. แสดงรายงานสถานะ

set -e

cd "$(dirname "$0")/../../.."

echo "╔══════════════════════════════════════════════════╗"
echo "║  🚀 CK-NEXUS Auto Setup — Free API Keys          ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Step 1: สร้าง .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ สร้าง .env จาก .env.example"
else
    echo "✅ .env มีอยู่แล้ว"
fi
echo ""

# Step 2: แสดง Provider ที่ต้องสร้าง key
echo "📋 ขั้นตอนการสร้าง Free API Keys:"
echo "══════════════════════════════════════"
echo ""
echo "🟢 LLM (AI) — เริ่มตรงนี้ก่อน:"
echo "   1. Groq (เร็วสุด)     → https://console.groq.com/keys"
echo "   2. OpenRouter (หลาย模型) → https://openrouter.ai/keys"
echo "   3. Google AI (Gemini)   → https://aistudio.google.com/apikey"
echo "   4. HuggingFace          → https://huggingface.co/settings/tokens"
echo "   5. DeepSeek             → https://platform.deepseek.com/api_keys"
echo ""
echo "🟡 Communication:"
echo "   6. Telegram Bot         → https://t.me/BotFather"
echo ""
echo "🔵 Search:"
echo "   7. Serper               → https://serper.dev/api-keys"
echo "   8. Tavily               → https://tavily.com/#api"
echo ""
echo "🟣 Database:"
echo "   9. Supabase             → https://supabase.com/dashboard/project/new"
echo "   10. Neon                → https://console.neon.tech"
echo ""
echo "🟠 Deployment:"
echo "   11. Vercel              → https://vercel.com/signup"
echo ""
echo "⚪ Other:"
echo "   12. GitHub Token        → https://github.com/settings/tokens"
echo "   13. Cloudflare R2       → https://dash.cloudflare.com/sign-up"
echo "   14. Composio            → https://app.composio.dev"
echo "   15. Stripe Test         → https://dashboard.stripe.com/register"
echo ""

# Step 3: รัน Python vault setup
echo "🔐 กำลังตั้งค่า Blind Vault..."
python3 -c "
from creator_app.credentials.autoscale.orchestrator import AutoScaleOrchestrator
orch = AutoScaleOrchestrator()
print('✅ Blind Vault พร้อมใช้งาน')
print(orch.report())
"

echo ""
echo "════════════════════════════════════════════════════════"
echo "📌 ขั้นตอนถัดไป:"
echo "   1. เปิด URL ด้านบนในเบราว์เซอร์"
echo "   2. สร้าง API key"
echo "   3. วาง key ด้วยคำสั่ง:"
echo "      python creator_app/credentials/scripts/ingest_key.py \"YOUR_KEY\""
echo ""
echo "   หรือเก็บหลาย key พร้อมกัน:"
echo "      python creator_app/credentials/scripts/ingest_key.py --file keys.txt"
echo ""
echo "   ดูสถานะ vault:"
echo "      python creator_app/credentials/scripts/ingest_key.py --list"
echo "════════════════════════════════════════════════════════"
