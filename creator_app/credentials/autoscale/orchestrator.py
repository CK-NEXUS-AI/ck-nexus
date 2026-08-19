"""Master Orchestrator — ระบบจัดการ API Key อัตโนมัติรอบด้าน.

รวม Multi-Key Pool + Health Monitor + Auto-Provision + Free Providers
เป็นระบบเดียวที่ทำงานอัตโนมัติ:

1. สแกน key ที่มี → เก็บใน vault
2. ตรวจสุขภาพทุก key → mark dead/active
3. ถ้า pool ว่าง → auto-provision หรือแนะนำ free provider
4. Failover อัตโนมัติ → สลับ key ที่ยังใช้ได้
5. รายงานสถานะทุกอย่าง

วิธีใช้:
    orch = AutoScaleOrchestrator()

    # เพิ่ม key
    orch.ingest("postman", "PMAK-xxxxx")

    # ใช้งาน
    key, entry = orch.get_key("postman")
    if key:
        # ใช้ key
        orch.mark_success(entry.vault_id)

    # สถานะ
    print(orch.report())
"""

from __future__ import annotations

from creator_app.credentials.autoscale.auto_provisioner import AutoProvisioner
from creator_app.credentials.autoscale.free_provider_registry import FreeProviderRegistry
from creator_app.credentials.autoscale.key_health_monitor import KeyHealthMonitor
from creator_app.credentials.autoscale.multi_key_pool import MultiKeyPool


class AutoScaleOrchestrator:
    """ระบบจัดการ API Key อัตโนมัติรอบด้าน.

    วิธีใช้:
        orch = AutoScaleOrchestrator()

        # เพิ่ม key หลายตัว
        orch.ingest("postman", "PMAK-key1")
        orch.ingest("postman", "PMAK-key2")
        orch.ingest("groq", "gsk_key1")

        # ดึง key สำหรับใช้งาน
        key, entry = orch.get_key("postman")
        if key:
            result = my_api_call(key)
            if result:
                orch.mark_success(entry.vault_id)
            else:
                orch.mark_dead(entry.vault_id)

        # ดูรายงาน
        print(orch.report())
    """

    def __init__(self, vault_dir: str | None = None):
        self.pool = MultiKeyPool(vault_dir=vault_dir)
        self.health = KeyHealthMonitor(pool=self.pool)
        self.provisioner = AutoProvisioner(pool=self.pool)
        self.registry = FreeProviderRegistry()

    def ingest(self, provider: str, key: str) -> str:
        """เพิ่ม key เข้า pool — return vault_id."""
        return self.pool.add_key(provider, key)

    def get_key(self, provider: str) -> tuple[str, object] | None:
        """ดึง key สำหรับใช้งาน — ได้ (key_value, entry)."""
        return self.pool.get_key_value(provider)

    def mark_success(self, vault_id: str) -> None:
        """มาร์คว่าใช้สำเร็จ."""
        self.pool.mark_success(vault_id)

    def mark_dead(self, vault_id: str, reason: str = "api_error") -> None:
        """มาร์คว่า key พัง — auto-failover."""
        self.pool.mark_dead(vault_id, reason)

    def provision(self, provider: str, api_key: str | None = None) -> object:
        """สร้าง key ใหม่."""
        return self.provisioner.provision(provider, api_key=api_key)

    def health_check(self) -> dict:
        """ตรวจสุขภาพทุก key."""
        return self.health.full_check()

    def report(self) -> str:
        """รายงานสถานะทั้งหมด."""
        pool_status = self.pool.status()
        health = self.health.full_check()
        provision_status = self.provisioner.get_status()
        registry_summary = self.registry.summary()

        lines = [
            "╔══════════════════════════════════════════════╗",
            "║  🔄 AUTO-SCALE ORCHESTRATOR — Status Report  ║",
            "╚══════════════════════════════════════════════╝",
            "",
            "📦 Key Pool Status:",
            f"   Total: {pool_status['total']}"
            f" | Active: {pool_status['active']}"
            f" | Dead: {pool_status['dead']}"
            f" | Quarantine: {pool_status['quarantine']}",
            "",
        ]

        # สถานะแต่ละ provider
        for prov in sorted(set(e["provider"] for e in self.pool.list_keys())):
            status = self.pool.status(prov)
            chain = self.pool.get_failover_chain(prov)
            lines.append(f"   🔑 {prov}:")
            lines.append(f"      Keys: {status['active']} active / {status['dead']} dead")
            if chain:
                lines.append(f"      Failover chain: {' → '.join(chain[:3])}")
            rec = self.health.get_recommendation(prov)
            lines.append(f"      Status: {rec}")

        # Health check
        if health:
            lines.append("")
            lines.append("🏥 Health Check:")
            for prov, ph in health.items():
                emoji = "✅" if not ph.needs_new_key else "⚠️"
                lines.append(f"   {emoji} {prov}: {ph.recommendation}")

        # Provisioning
        needing_keys = provision_status.get("providers_needing_keys", [])
        if needing_keys:
            lines.append("")
            lines.append("🚨 Keys Needed:")
            for prov in needing_keys:
                url = self.registry.by_name(prov)
                if url:
                    lines.append(f"   → {prov}: {url.signup_url}")
                else:
                    lines.append(f"   → {prov}: ต้องสร้าง key ใหม่")

        # Free providers
        lines.append("")
        lines.append(f"🌐 Free Providers Available: {registry_summary['total']}")
        for cat, count in registry_summary.get("by_category", {}).items():
            lines.append(f"   {cat}: {count} providers")

        lines.append("")
        lines.append("═" * 50)
        return "\n".join(lines)

    def full_setup_guide(self, category: str = "llm") -> str:
        """แสดงคู่มือ setup provider ฟรี."""
        return self.registry.setup_guide(category)

    def all_free_providers(self) -> str:
        """แสดง provider ฟรีทั้งหมด."""
        return self.registry.full_setup_guide()
