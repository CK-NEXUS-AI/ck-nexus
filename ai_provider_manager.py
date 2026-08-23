#!/usr/bin/env python3
"""CK-NEXUS AI Provider Manager — จุดเริ่มต้นหลัก.

รวมทุกระบบเข้าด้วยกัน:
- Universal Credential Broker
- Sticky Free Fallback Key Pool (เหลือ <=85% -> FREE_ONLY)
- Capability Registry
- Auto-Connect Manager
- Gmail Universal Bridge
- Local Ollama fallback when paid APIs are disabled

วิธีใช้:
  python ai_provider_manager.py start    # เริ่มทุกระบบ
  python ai_provider_manager.py status   # แสดงสถานะ
  python ai_provider_manager.py scan     # สแกนอีเมล Gmailใหม่
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from creator_app.core.auto_connect_manager import (
    AutoConnectConfig,
    AutoConnectManager,
)
from creator_app.credentials import (
    CapabilityRegistry,
    CredentialBroker,
    FreeFallbackKeyPool,
)


class AIProviderManager:
    """ผู้จัดการ AI + Gmail ระบบเดียวจบ — เริ่มทำงานพร้อมกันทุกอย่าง."""

    def __init__(self) -> None:
        self.broker = CredentialBroker.from_environment()
        self.keypool = FreeFallbackKeyPool.from_environment()
        self.registry = CapabilityRegistry()
        self.auto_connect = AutoConnectManager(
            config=AutoConnectConfig(
                health_check_interval_sec=float(os.getenv("HEALTH_CHECK_INTERVAL_SEC", "30")),
                max_retry_attempts=int(os.getenv("MAX_RETRY_ATTEMPTS", "5")),
                circuit_breaker_threshold=int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3")),
            )
        )
        self._started = False
        self._gmail_bridge = None

    async def start(self) -> None:
        """เริ่มระบบทั้งหมด — เชื่อม Gmail + AI providers + auto-connect."""
        self._started = True
        print("🚀 เริ่มต้น CK-NEXUS AI Provider Manager...")
        print()

        if self.keypool:
            print(f"🔑 พบ {len(self.keypool.specs)} AI providers ที่ตั้งค่าแล้ว")
            for spec in self.keypool.specs:
                priority = {"groq": "หลัก", "openrouter": "สำรอง1", "openai": "สำรอง2"}.get(
                    spec.id, "สำรอง"
                )
                print(f"   • {spec.id} ({priority}) — model: {spec.model}")
            policy = self.keypool.policy_status()
            print(
                "💸 Credit Guard: "
                f"{policy['mode']} — trigger เมื่อเครดิต paid เหลือ <= "
                f"{policy['remaining_threshold_pct']:.0f}%"
            )

        gmail_id = os.getenv("GOOGLE_CLIENT_ID", "")
        gmail_refresh = os.getenv("GOOGLE_REFRESH_TOKEN", "")
        if gmail_id and gmail_refresh:
            print("\n📧 Gmail: ✅ เชื่อมต่อ (spinlnw10@gmail.com)")
            from creator_app.credentials.gmail_oauth_connector import GmailConnector

            self._gmail_bridge = GmailConnector(self.broker)

        await self.auto_connect.start()
        interval = int(self.auto_connect.config.health_check_interval_sec)
        print(f"\n🔌 Auto-Connect: เปิด — ตรวจสุขภาพทุก {interval}วินาที")
        print("🛡️ Security: Fail-Closed — ป้องกันการเปิดเผย credential")
        print()
        print("✅ ระบบพร้อมใช้งานแล้ว!")
        print("   ใช้ 'python ai_provider_manager.py status' เพื่อตรวจสอบสถานะ")
        print("   ใช้ 'python ai_provider_manager.py scan' เพื่อสแกนอีเมล Gmailใหม่")

    async def stop(self) -> None:
        """หยุดทุกระบบและบันทึกสถานะ."""
        if self.auto_connect:
            await self.auto_connect.stop()
        self._started = False
        print("🛑 ระบบหยุดทำงานและบันทึกสถานะแล้ว")

    def _local_fallback_ready(self) -> bool:
        enabled = os.getenv("CKNEXUS_OLLAMA_ENABLED", "false").strip().lower()
        return enabled in {"1", "true", "yes", "on"} and bool(os.getenv("OLLAMA_MODEL", "").strip())

    def status(self) -> dict:
        """แสดงสถานะทุกระบบ."""
        result = {
            "started": self._started,
            "gmail": {
                "client_id_configured": bool(os.getenv("GOOGLE_CLIENT_ID")),
                "refresh_token_configured": bool(os.getenv("GOOGLE_REFRESH_TOKEN")),
                "connected": bool(
                    os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_REFRESH_TOKEN")
                ),
            },
            "providers": [],
            "auto_connect": self.auto_connect.status() if self.auto_connect else None,
            "local_fallback": {
                "provider": "ollama",
                "ready": self._local_fallback_ready(),
                "model_configured": bool(os.getenv("OLLAMA_MODEL", "").strip()),
            },
        }

        if self.keypool:
            statuses = self.keypool.status()
            for s in statuses:
                result["providers"].append(
                    {
                        "id": s.key_id,
                        "provider": s.provider,
                        "free": s.free,
                        "healthy": bool(s.healthy),
                        "exhausted": s.exhausted,
                        "quota_pct": s.quota_percentage_used,
                        "source": s.source,
                    }
                )
            result["free_fallback"] = self.keypool.free_fallback
            result["credit_policy"] = self.keypool.policy_status()

        return result

    def print_status(self) -> None:
        """พิมพ์แดชบอร์ดสถานะอย่างเต็มระบบ."""
        status = self.status()

        print()
        print("📊 CK-NEXUS Universal System — สถานะทั้งหมด")
        print("─" * 50)

        if status["gmail"]["connected"]:
            print("📧 Gmail (spinlnw10@gmail.com): ✅ เชื่อมต่อ")
        else:
            print("📧 Gmail: ❌ ยังไม่ได้ตั้งค่า")

        if status["providers"]:
            print("\n🤖 AI Providers:")
            priority_labels = {
                "groq": "หลัก",
                "openrouter": "สำรอง1",
                "openai": "สำรอง2",
                "anthropic": "สำรอง3",
                "deepseek": "สำรอง4",
            }
            for p in status["providers"]:
                label = priority_labels.get(p["provider"], p["provider"])
                if p["healthy"]:
                    icon = "✅"
                elif p["exhausted"]:
                    icon = "🔴"
                else:
                    icon = "⚠️"

                quota = ""
                if p["quota_pct"] is not None:
                    remaining = 100 - p["quota_pct"]
                    quota = f" เครดิตเหลือ {remaining:.0f}%"

                print(f"   {icon} {label:<10} {p['provider']:<12} (ฟรี: {p['free']}){quota}")

            policy = status.get("credit_policy", {})
            print(
                "\n🔄 Credit Guard: "
                f"{policy.get('mode', 'UNKNOWN')} — FREE_ONLY เมื่อ paid credit เหลือ <= "
                f"{policy.get('remaining_threshold_pct', 85):.0f}%"
            )
            print(
                "🧱 Remote free-tier in FREE_ONLY: "
                + ("เปิด" if policy.get("allow_remote_free") else "ปิด (local-first)")
            )
            print(
                "🖥️ Local Ollama fallback: "
                + ("✅ พร้อม" if status["local_fallback"]["ready"] else "⚠️ ยังไม่พร้อม")
            )
            print("🛡️ Security: Fail-Closed — paid API ถูกตัดออกเมื่อ FREE_ONLY ทำงาน")
        else:
            print("\n🔑 AI Providers: ใส่ API key ใน .env เพื่อเริ่มใช้งาน")

        print()

    def print_dashboard(self) -> None:
        """พิมพ์แดชบอร์ดแบบย่อ."""
        print()
        print("📊 CK-NEXUS Universal System — สถานะทั้งหมด")
        print("─" * 50)

        pool = FreeFallbackKeyPool.from_environment()
        if pool:
            statuses = pool.status()
            for s in statuses:
                icon = "✅" if s.healthy else ("🔴" if s.exhausted else "⚠️")
                pct = 100 - (s.quota_percentage_used or 0)
                print(f"   {icon} {s.provider:<12} เครดิตเหลือ {pct:.0f}%")
            policy = pool.policy_status()
            print(
                f"\n🔄 Credit Guard: {policy['mode']} — trigger ที่เหลือ "
                f"{policy['remaining_threshold_pct']:.0f}%"
            )
        print("🛡️ Security: Fail-Closed")
        print()

    def scan_gmail_emails(self) -> dict:
        """สแกนอีเมล Gmail ใหม่และสกัดข้อมูลสำคัญ."""
        from creator_app.credentials.gmail_universal_bridge import GmailUniversalBridge

        if not os.getenv("GOOGLE_CLIENT_ID"):
            print("❌ ตั้งค่า GOOGLE_CLIENT_ID และ GOOGLE_REFRESH_TOKEN ใน .env ก่อน")
            return {}

        bridge = GmailUniversalBridge()
        result = asyncio.run(bridge.authenticate())
        if not result:
            print("❌ ไม่สามารถเชื่อม Gmail ได้ — ตรวจสอบ credentials")
            return {}

        emails = bridge.list_unread_emails()
        print(f"📬 พบอีเมลใหม่: {len(emails)} ฉบับ")

        for email in emails:
            extracted = bridge.extract_otp_and_links(email)
            print(f"   • {email.subject}")
            if extracted.otp_codes:
                print(f"     🔑 OTP: {list(extracted.otp_codes)[:3]}")
            if extracted.verification_links:
                print(f"     🔗 ลิงก์: {len(extracted.verification_links)} รายการ")

        return {"scanned": len(emails)}

    def chat(self, prompt: str) -> str:
        """เลือก provider ตาม Credit Guard; FREE_ONLY จะไม่คืน paid API key."""
        if not prompt.strip():
            return "❌ prompt ว่าง"
        if not self.keypool:
            if self._local_fallback_ready():
                return f"✅ ใช้ local Ollama (model: {os.getenv('OLLAMA_MODEL')}) — API credit = 0"
            return "❌ ไม่มี AI provider หรือ local model ที่พร้อมใช้งาน"

        selection = self.keypool.acquire()
        if selection is None:
            if self.keypool.free_only_mode and self._local_fallback_ready():
                return (
                    f"✅ FREE_ONLY → local Ollama (model: {os.getenv('OLLAMA_MODEL')}) "
                    "— paid API disabled"
                )
            if self.keypool.free_only_mode:
                return "⚠️ FREE_ONLY ทำงานแล้ว — paid API disabled; local Ollama ยังไม่พร้อม"
            if self.keypool.free_fallback:
                return "⚠️ ไม่มีคีย์พร้อม — ต้องใช้ local/offline fallback"
            return "❌ ไม่มี AI provider พร้อมใช้งาน"

        return (
            f"✅ ใช้ {selection.provider} (model: {selection.model}) — "
            f"key_id: {selection.key_id}; free={selection.free}"
        )


def main() -> int:
    import dotenv

    dotenv.load_dotenv()
    command = sys.argv[1] if len(sys.argv) > 1 else "status"

    if command == "status":
        mgr = AIProviderManager()
        mgr.print_status()
        return 0

    if command == "dashboard":
        mgr = AIProviderManager()
        mgr.print_dashboard()
        return 0

    if command == "scan":
        mgr = AIProviderManager()
        mgr.scan_gmail_emails()
        return 0

    if command == "start":
        mgr = AIProviderManager()

        async def run() -> None:
            await mgr.start()
            try:
                while True:
                    await asyncio.sleep(60)
            except KeyboardInterrupt:
                await mgr.stop()

        asyncio.run(run())
        return 0

    if command == "test":
        print("🧪 ทดสอบระบบ CK-NEXUS...")
        import subprocess

        result = subprocess.run(
            ["python", "-m", "pytest", "creator_app/credentials/tests/", "-v"],
            capture_output=False,
        )
        return result.returncode

    print(f"Unknown command: {command}")
    print("Available: start, status, dashboard, scan, test")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
