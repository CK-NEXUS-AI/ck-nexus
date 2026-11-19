#!/usr/bin/env python3
"""CK-NEXUS Credential Dashboard — แสดงสถานะเชื่อมต่อแบบเรียลไทม์.

ใช้: python creator_app/credentials/scripts/dashboard.py [--json]
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from creator_app.credentials.llm_keypool import LlmKeyPool


def _truncate(text: str, length: int = 20) -> str:
    return text[:length] + "..." if len(text) > length else text


def print_dashboard() -> int:
    print()
    print("📊 CK-NEXUS — Universal Credential Status")
    print("─" * 50)

    # Gmail
    gmail_id = os.getenv("GOOGLE_CLIENT_ID", "")
    gmail_refresh = os.getenv("GOOGLE_REFRESH_TOKEN", "")
    gmail_connected = bool(gmail_id and gmail_refresh)

    if gmail_connected:
        print(f"📧 Gmail: ✅ เชื่อมต่อ (Client ID: {_truncate(gmail_id)})")
    else:
        print("📧 Gmail: ❌ ยังไม่ได้ตั้งค่า (ใช้ get_gmail_token.py)")

    print()

    # AI Providers
    pool = LlmKeyPool.from_environment()
    if pool is None:
        print("🔑 AI Providers: ไม่มีคีย์ใดๆ ตั้งค่าอยู่")
        print("   ใส่ API key ใน .env เพื่อเริ่มใช้งาน")
        return 0

    print(f"🔑 ผู้ให้บริการที่ลงทะเบียน: {len(pool.specs)} ราย")
    print()

    statuses = pool.status()
    for status in statuses:
        if status.healthy:
            icon = "✅"
        elif status.exhausted:
            icon = "🔴"
        else:
            icon = "⚠️"

        quota_str = ""
        if status.quota_percentage_used is not None:
            pct = status.quota_percentage_used
            if pct >= 95:
                quota_str = f" ⚠️ ใช้ {pct:.0f}% → พร้อมสลับ"
            else:
                quota_str = f" เครดิตเหลือ {100 - pct:.0f}%"

        source_str = "✅ ใช้งานได้" if status.source == "environment" else f"({status.source})"
        print(f"   {icon} {status.provider:<12} {source_str}{quota_str}")

    print()
    print("🔄 สลับอัตโอโมเติฟ: เปิด — ที่ 95%")
    print("🛡️ โหมดความปลอดภัย: Fail-Closed — ไม่ดำเนินการถ้าไม่ชัดเจน")
    print()

    return 0


def print_json_status() -> int:
    pool = LlmKeyPool.from_environment()
    statuses = pool.status() if pool else []

    data = {
        "gmail": {
            "client_id_configured": bool(os.getenv("GOOGLE_CLIENT_ID")),
            "refresh_token_configured": bool(os.getenv("GOOGLE_REFRESH_TOKEN")),
            "connected": bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_REFRESH_TOKEN")),
        },
        "providers": [
            {
                "id": s.key_id,
                "provider": s.provider,
                "model": s.model,
                "free": s.free,
                "healthy": bool(s.healthy),
                "exhausted": s.exhausted,
                "quota_pct": s.quota_percentage_used,
                "source": s.source,
            }
            for s in statuses
        ],
        "free_fallback": pool.free_fallback if pool else True,
    }
    print(json.dumps(data, indent=2, default=str))
    return 0


def main() -> int:
    if "--json" in sys.argv:
        return print_json_status()
    return print_dashboard()


if __name__ == "__main__":
    raise SystemExit(main())
