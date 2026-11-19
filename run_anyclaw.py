#!/usr/bin/env python3
"""AnyClaw Auto-Run Script — เรียกใช้งานอัตโนมัติทั้งหมด.

รัน: python run_anyclaw.py
"""

import sys

sys.path.insert(0, ".")

from creator_app.ai_team.universal_system import UniversalSystem
from creator_app.core.self_capability_manager import SelfCapabilityManager


def main():
    print("=" * 60)
    print("🚀 AnyClaw — Auto-Run System")
    print("=" * 60)
    print()

    # ─── ขั้นที่ 1: รู้จักตัวเอง ───
    print("📋 ขั้นที่ 1: ระบบรู้จักตัวเอง")
    print("-" * 40)
    manager = SelfCapabilityManager()
    print(manager.explain_what_i_can_do())
    print()

    # ─── ขั้นที่ 2: ค้นหาความสามารถใหม่ ───
    print("🔍 ขั้นที่ 2: ค้นหาความสามารถใหม่")
    print("-" * 40)
    discovery = manager.discover_new_capabilities()
    print(f"  ค้นพบใหม่: {discovery['new_capabilities_added']} อย่าง")
    print(f"  รวมทั้งหมด: {discovery['total_capabilities']} อย่าง")
    print(f"  แหล่งที่ตรวจสอบ: {', '.join(discovery['sources_checked'])}")
    if discovery['discovered']:
        print("  ความสามารถใหม่:")
        for cap in discovery['discovered']:
            print(f"    ✨ {cap}")
    print()

    # ─── ขั้นที่ 3: แสดงข้อจำกัด ───
    print("⚠️ ขั้นที่ 3: ข้อจำกัดและทางแก้")
    print("-" * 40)
    limitations = manager.get_limitations_and_workarounds()
    for lim in limitations["cannot_do"]:
        print(f"  ❌ {lim['item']}")
        print(f"     ✅ {lim['workaround']}")
    print()

    # ─── ขั้นที่ 4: ทดสอบ Universal System ───
    print("🧠 ขั้นที่ 4: ทดสอบ Universal System")
    print("-" * 40)
    system = UniversalSystem()

    test_requests = [
        "สร้างระบบเชื่อม Gmail อ่านอีเมล บันทึก Sheets",
        "เขียนโค้ด Python API สำหรับจัดการออเดอร์",
        "ตรวจสอบ security audit ทั้งระบบ",
    ]

    for req in test_requests:
        print(f"\n  📝 คำขอ: {req}")
        result = system.process(req)
        # แสดงเฉพาะบรรทัดสำคัญ
        for line in result.split("\n"):
            keywords = ["เครื่องมือ", "ทีม", "ขั้นตอน", "เวลา", "แพลตฟอร์ม", "ความปลอดภัย"]
            if any(kw in line for kw in keywords):
                print(f"    {line.strip()}")
    print()

    # ─── ขั้นที่ 5: สถานะรวม ───
    print("📊 ขั้นที่ 5: สถานะรวม")
    print("-" * 40)
    status = system.status()
    print(f"  ทีม AI: {status['team']['agents'].__len__()} คน")
    print(f"  เครื่องมือ: {status['tools_registered']} รายการ")
    print(f"  แหล่งข้อมูล: {status['data_sources']} แหล่ง")
    print(f"  แพลตฟอร์ม: {status['platform']}")
    print(f"  Audit entries: {status['audit_entries']} รายการ")
    print()

    # ─── สรุป ───
    print("=" * 60)
    print("✅ AnyClaw Auto-Run เสร็จสมบูรณ์!")
    print("=" * 60)
    print()
    print("🚀 ขั้นตอนถัดไป:")
    print("  1. รัน MCP Server: python -m creator_app.agnes.mcp_server")
    print("  2. เชื่อม ChatGPT: ใส่ http://localhost:8765/openapi.json ใน Actions")
    print("  3. สั่งงานจากแชทได้เลย!")
    print()
    print("💡 ตัวอย่างคำสั่งจาก ChatGPT:")
    print('  "ให้ AnyClaw เช็คสถานะระบบ"')
    print('  "ให้ AnyClaw เขียนโค้ด Python API"')
    print('  "ให้ AnyClaw ตรวจสอบ security"')
    print('  "ให้ AnyClaw ดูความสามารถทั้งหมด"')

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
