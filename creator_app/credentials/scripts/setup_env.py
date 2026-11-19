#!/usr/bin/env python3
"""Setup script สำหรับสร้างไฟล์ .env พร้อมระบบ Universal Credential Broker.

ใช้:  python creator_app/credentials/scripts/setup_env.py [--interactive]

ยากรุป:
- สร้าง .env พร้อมตัวแปรทั้งหมดที่ระบบต้องการ
- ไม่เก็บหรือส่ง credential ใดๆ ออกไป
- ใช้ environment variables หรือ stdin เพื่อกรอกค่าเท่านั้น
"""

from __future__ import annotations

import sys
from pathlib import Path

ENV_TEMPLATE = """\
# ==========================================
# 📧 GMAIL OAUTH — เชื่อม Gmail ผ่าน OAuth2 (ไม่ขอรหัสผ่าน)
# ==========================================
# ได้รับจาก Google Cloud Console -> APIs & Services -> Credentials
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=

# วิธีขอ Refresh Token (ทำบนเครื่องคุณเอง — ไม่ส่งให้ใคร):
#   python creator_app/credentials/scripts/get_gmail_token.py

# ==========================================
# 🔑 AI Providers — เติม API Key ของคุณเท่านั้น
# ==========================================
OPENAI_API_KEY=
GROQ_API_KEY=
ANTHROPIC_API_KEY=
DEEPSEEK_API_KEY=
GEMINI_API_KEY=
MOONSHOT_API_KEY=
MISTRAL_API_KEY=
TOGETHER_API_KEY=
SAMBANOVA_API_KEY=
ZHIPU_API_KEY=
DASHSCOPE_API_KEY=
OPENROUTER_API_KEY=
CEREBRAS_API_KEY=

# ==========================================
# 🐙 GitHub App (ถ้ามี)
# ==========================================
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_APP_INSTALLATION_ID=
GITHUB_INSTALLATION_TOKEN=

# ==========================================
# ⚙️ ระบบจัดการ Credential Broker
# ==========================================
# สลับอัตโนมัติเมื่อใช้เกิน 95% (ค่าเริ่มต้น)
CREDIT_WARNING_THRESHOLD_PERCENT=95
# หมุนเวียนคีย์ใหม่เมือเหลือน้อยกว่า 5%
CREDIT_ROTATION_THRESHOLD_PERCENT=5
# พักผู้ให้บริการที่ล้มเหลว 5 นาที ก่อนลองใหม่
PROVIDER_RETRY_DELAY_SEC=300
# เปิด/ปิด circuit breaker
PROVIDER_CIRCUIT_BREAKER_ENABLED=true
# จำนวนครั้งสูงสุดที่ลองก่อนยอมรับการล้มเหลว
PROVIDER_MAX_RETRY_ATTEMPTS=5

# ==========================================
# 🛡️ โหมดความปลอดภัย (Fail-Closed เป็นค่าเริ่มต้น)
# ==========================================
SECURITY_FAIL_CLOSED=true
# ไม่บันทึก credential ใน log เด็ดขาด
SECURITY_REDACT_SECRETS=true
# ใช้ vault เข้ารหลัสไหม? (ต้องการ CKNEXUS_VAULT_KEY)
CREDENTIAL_VAULT_ENABLED=false
CREDENTIAL_VAULT_PATH=~/.cknexus/credential_vault.db
CKNEXUS_VAULT_KEY=

# ==========================================
# 📊 Auto-Connect Manager
# ==========================================
HEALTH_CHECK_INTERVAL_SEC=30
MAX_RETRY_ATTEMPTS=5
CIRCUIT_BREAKER_THRESHOLD=3
CIRCUIT_COOLDOWN_SEC=60
OFFLINE_MODE_ENABLED=true

# ==========================================
# 🔄 ระบบสลับ AI (Multi-Provider Failover)
# ==========================================
# ลำดับความสำคัฐ (ลำดับเลขยิบถ่วง): 1=หลัก, 2=สำรอง1, 3=สำรอง2
LLM_PROVIDER_PRIORITY_1=groq
LLM_PROVIDER_PRIORITY_2=openrouter
LLM_PROVIDER_PRIORITY_3=openai
LLM_PROVIDER_PRIORITY_4=anthropic
LLM_PROVIDER_PRIORITY_5=deepseek

# ระบบจะสลับไป provider ที่อยู่ในลำดับถัดไปเมื่อเจ้าหลักล้มเหลว
# ไม่หยุดงาน ไม่กระตายไปขอ key ใหม่
"""


def main() -> int:
    env_path = Path(".env")
    interactive = "--interactive" in sys.argv

    if env_path.exists() and not interactive:
        existing = env_path.read_text(encoding="utf-8")
        if "GOOGLE_CLIENT_ID=" in existing:
            print("✅ .env มีอยู่แล้วพร้อมค่า Gmail credentials")
            print("   (ข้ามการสร้าง — ใช้ --overwrite เพื่อสร้างใหม่)")
            return 0

    try:
        env_path.write_text(ENV_TEMPLATE, encoding="utf-8", errors="strict")
        # Use Path.write_text with appropriate mode
    except FileExistsError:
        print(f"❌ {env_path} มีอยู่แล้ว — ใช้ --overwrite เพื่อเขียนทับ")
        return 1

    # Re-write with correct mode
    if "--overwrite" in sys.argv:
        env_path.write_text(ENV_TEMPLATE, encoding="utf-8")

    print(f"✅ สร้าง {env_path} เรียบร้อยแล้ว")
    print()
    if interactive:
        print("ขั้นตอนต่อไป:")
        print("  1. แก้ไข .env ในไฟล์ที่สร้าง")
        print("  2. ใช้ Google Cloud Console ขอ GOOGLE_CLIENT_ID/SECRET")
        print("  3. รัน get_gmail_token.py เพื่อขอ GOOGLE_REFRESH_TOKEN")
        print("  4. ใส่ API keys จากผู้ให้บริการ AI ที่คุณมี")
        print("  5. รันทดสอบ: python -m pytest creator_app/credentials/tests/ -v")
    else:
        print("แก้ไข .env แล้วเติมค่าที่จำเป็น")
    return 0


if __name__ == "__main__":
    sys.exit(main())
