# CK-NEXUS Autonomous Development Platform Knowledge Base

สถานะ: Working handoff / architecture baseline + image landscape synthesis
วันที่สร้าง/อัปเดต: 2026-10-31
Repository: `CK-NEXUS-AI/ck-nexus`

โฟลเดอร์นี้คือจุดเริ่มต้นมาตรฐานสำหรับ AI หรือผู้พัฒนาที่เข้ามาทำงาน CK-NEXUS ในครั้งถัดไป ห้ามถือเอกสารในนี้ว่าเป็น production approval; ให้ตรวจ `CURRENT_STATE.md`, branch, commit และ CI จริงก่อนลงมือทุกครั้ง

## อ่านตามลำดับ

1. [CURRENT_STATE.md](CURRENT_STATE.md) — สิ่งที่ตรวจจริงแล้วและข้อจำกัดปัจจุบัน
2. [IMPLEMENTATION_BACKLOG.md](IMPLEMENTATION_BACKLOG.md) — งาน P0–P3 ที่เรียงลำดับจากผลสแกน
3. [ARCHITECTURE.md](ARCHITECTURE.md) — แบบจำลอง Autonomous Development Platform V2
4. [IMAGE_DESIGN_SYNTHESIS.md](IMAGE_DESIGN_SYNTHESIS.md) — pattern ที่สกัดจากภาพ 104 รายการ
5. [IMAGE_SCAN_100_CATALOG.md](IMAGE_SCAN_100_CATALOG.md) — catalog และ SHA-256 ของภาพที่สแกน
6. [CONNECTORS.md](CONNECTORS.md) — connector/tool registry และ risk boundary
7. [AGNES.md](AGNES.md) — ความสามารถและ execution boundary ของ AGNES
8. [AUTOMATIONS.md](AUTOMATIONS.md) — automation catalog, trigger, owner และ rollback
9. [SKILLS_AND_TOOLS.md](SKILLS_AND_TOOLS.md) — skills และเครื่องมือที่ใช้กับงานนี้
10. [IMAGE_RESEARCH.md](IMAGE_RESEARCH.md) — ผลสแกนภาพ Pinterest เดิม
11. [NEXT_AI_HANDOFF.md](NEXT_AI_HANDOFF.md) — checklist สำหรับ AI รอบถัดไป
12. [manifest.json](manifest.json) — index เดิมของ Knowledge Base
13. [image_scan_manifest.json](image_scan_manifest.json) — machine-readable manifest ของภาพ 104 รายการ

## Image scan scope

สแกนภาพอ้างอิง 104 รายการจาก 10 หมวด: platform engineering, AI coding agents, GitOps/CI-CD, DevSecOps, sandbox/policy, observability/SRE, RAG/knowledge graph, event orchestration, progressive delivery และ governance/cost/tenancy/developer experience. Repository เก็บ derived metadata และ design insights ไม่ฝังภาพต้นฉบับที่อาจมีลิขสิทธิ์.

## Operating rule

AI เป็น planner/reviewer/worker ไม่ใช่ authority. ทุกการแก้โค้ดต้องมี work identity, base SHA, isolated branch/workspace, verification evidence และสถานะชัดเจน. ห้ามข้าม approval เพียงเพราะ test ผ่าน. ห้ามบันทึก token, API key, credential, cookie หรือข้อมูลลับใน repository.

## Next recommended sequence

`P0.1 durable workflow → P0.2 envelopes → P0.3 policy gate → P0.4 connector capabilities → P0.5 AGNES sandbox → P1.1 idempotency → P1.2 golden paths → P1.3 GitOps reconciliation`