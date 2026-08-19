#!/usr/bin/env python3
"""Full Demo — แสดงระบบทั้งหมดทำงานอัตโนมัติ.

วิธีใช้:
    python run_full_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from creator_app.credentials.autoscale.orchestrator import AutoScaleOrchestrator
from creator_app.credentials.autoscale.free_provider_registry import FreeProviderRegistry
from creator_app.ai_team.universal_system import UniversalSystem


def main() -> None:
    print("=" * 60)
    print("🚀 CK-NEXUS FULL SYSTEM DEMO")
    print("=" * 60)

    # ═══ 1. Auto-Scale System ═══
    print("\n📦 1. AUTO-SCALE SYSTEM")
    print("-" * 40)
    orch = AutoScaleOrchestrator()

    # จำลอง: เพิ่ม key หลายตัว
    print("   เพิ่ม key หลายตัว (จำลอง)...")
    orch.ingest("postman", "PMAK-demo1_key1234567890abcdef")
    orch.ingest("postman", "PMAK-demo2_key1234567890abcdef")
    orch.ingest("groq", "gsk_demo_key1234567890abcdef12")
    orch.ingest("openai", "sk-demo_key1234567890abcdef12")

    # ดึง key
    result = orch.get_key("postman")
    if result:
        key, entry = result
        print(f"   ✅ ได้ key: {entry.vault_id} (provider: {entry.provider})")

    # จำลอง: ใช้สำเร็จ
    orch.mark_success(entry.vault_id)
    print("   ✅ mark_success — key ยังใช้ได้")

    # จำลอง: key แรกพัง
    vid1 = orch.pool.list_keys("postman")[0]["vault_id"]
    orch.mark_dead(vid1, "rate_limited")
    orch.mark_dead(vid1, "rate_limited")
    orch.mark_dead(vid1, "rate_limited")
    print(f"   ⚠️ mark_dead x3 — key {vid1[:15]}... ถูกปิดใช้งาน")

    # Failover — ได้ key ตัวถัดไป
    result2 = orch.get_key("postman")
    if result2:
        _, entry2 = result2
        print(f"   🔄 Failover — ได้ key ใหม่: {entry2.vault_id}")

    # รายงาน
    print("\n" + orch.report())

    # ═══ 2. Free Providers ═══
    print("\n🌐 2. FREE API PROVIDERS")
    print("-" * 40)
    registry = FreeProviderRegistry()
    summary = registry.summary()
    print(f"   รวมทั้งหมด: {summary['total']} providers")
    for cat, count in summary["by_category"].items():
        print(f"   {cat}: {count} providers")

    # แสดง top 5 LLM ฟรี
    llm = registry.by_category("llm")
    print(f"\n   🤖 Top LLM ฟรี:")
    for p in llm[:5]:
        print(f"   {p.display_name}")
        print(f"      {p.signup_url}")
        print(f"      Quota: {p.free_quota}")

    # ═══ 3. Universal System ═══
    print("\n🧠 3. UNIVERSAL SYSTEM")
    print("-" * 40)
    system = UniversalSystem()

    # ทดสอบ process
    result = system.process("สร้างระบบเชื่อม Gmail อ่านอีเมล บันทึก Sheets")
    print(f"   ✅ process() สำเร็จ ({len(result)} chars)")

    # ทดสอบ status
    status = system.status()
    agents = len(status['team'].get('agents', []))
    print(f"   ✅ status(): team={agents} members, tools={status['tools_registered']}")

    # ทดสอบ capabilities
    caps = system.list_capabilities()
    print(f"   ✅ capabilities: {caps['team_members']} team, {caps['tools']} tools, {caps['categories']} categories")

    # ═══ 4. Intelligence Modules ═══
    print("\n⚡ 4. INTELLIGENCE MODULES")
    print("-" * 40)
    from creator_app.ai_team.intelligence import (
        SmartCache, AutoModelRouter, SelfCorrectionLoop,
        MultiPerspectiveThinker, SemanticMemory,
    )

    # SmartCache
    cache = SmartCache()
    cache.set("test query", "cached response")
    cached = cache.get("test query")
    print(f"   ✅ SmartCache: hit={'yes' if cached else 'no'}, stats={cache.stats}")

    # AutoModelRouter
    router = AutoModelRouter()
    model = router.select_model("วิเคราะห์เชิงลึก security audit")
    print(f"   ✅ AutoRouter: {model.name} (speed={model.speed_rating}/10, quality={model.quality_rating}/10)")

    # SelfCorrection
    sc = SelfCorrectionLoop()
    check = sc.verify("test", "this is a confident response with evidence and proof")
    print(f"   ✅ SelfCorrection: {check.summary}")

    # MultiPerspective
    thinker = MultiPerspectiveThinker()
    analysis = thinker.analyze("สร้างระบบชำระเงิน online")
    print(f"   ✅ MultiPerspective: {len(analysis.perspectives)} angles, risk={analysis.overall_risk}")

    # SemanticMemory
    mem = SemanticMemory()
    mem.store("CK-NEXUS uses Evidence-First", "principle", importance=0.9)
    results = mem.recall("CK-NEXUS Evidence")
    print(f"   ✅ SemanticMemory: {mem.stats()['total_memories']} entries")

    # ═══ 5. Summary ═══
    print("\n" + "=" * 60)
    print("✅ ระบบทั้งหมดทำงานสำเร็จ!")
    print("=" * 60)
    print("""
📊 สรุป:
   🔐 Blind Vault: พร้อมเก็บ API key แบบตาบอด
   🔄 Multi-Key Pool: พร้อม failover อัตโนมัติ
   🌐 Free Providers: 20 providers ฟรี
   🧠 Intelligence: Cache + Router + Correction + Memory + Perspective
   🤖 Universal System: 6 subsystems รวมเป็นหนึ่ง

📌 ขั้นตอนถัดไป:
   1. สร้าง API key ฟรีจาก providers ด้านบน
   2. วาง key: python creator_app/credentials/scripts/ingest_key.py "YOUR_KEY"
   3. ระบบจะจัดการเองทั้งหมด!
""")


if __name__ == "__main__":
    main()
