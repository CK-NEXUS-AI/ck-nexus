# CK-NEXUS Autonomous Development Platform Knowledge Base

สถานะ: Working handoff / architecture baseline
วันที่สร้าง: 2026-10-31
Repository: `CK-NEXUS-AI/ck-nexus`

โฟลเดอร์นี้เป็นจุดเริ่มต้นมาตรฐานสำหรับ AI หรือผู้พัฒนาที่เข้ามาทำงาน CK-NEXUS ในครั้งถัดไป ห้ามถือเอกสารในนี้ว่าเป็น production approval; ให้ตรวจ `CURRENT_STATE.md`, branch, commit และ CI จริงก่อนลงมือทุกครั้ง

## อ่านตามลำดับ

1. [CURRENT_STATE.md](CURRENT_STATE.md) — สิ่งที่ตรวจจริงแล้วและข้อจำกัดปัจจุบัน
2. [ROADMAP.md](ROADMAP.md) — ลำดับพัฒนาที่ต้องทำต่อ
3. [ARCHITECTURE.md](ARCHITECTURE.md) — แบบจำลอง Autonomous Development Platform V2
4. [CONNECTORS.md](CONNECTORS.md) — connector/tool registry และ risk boundary
5. [AGNES.md](AGNES.md) — ความสามารถและ execution boundary ของ AGNES
6. [AUTOMATIONS.md](AUTOMATIONS.md) — automation catalog, trigger, owner และ rollback
7. [SKILLS_AND_TOOLS.md](SKILLS_AND_TOOLS.md) — skills และเครื่องมือที่ใช้กับงานนี้
8. [IMAGE_RESEARCH.md](IMAGE_RESEARCH.md) — ผลสแกนภาพ Pinterest และ requirement ที่สกัดได้
9. [NEXT_AI_HANDOFF.md](NEXT_AI_HANDOFF.md) — checklist สำหรับ AI รอบถัดไป
10. [manifest.json](manifest.json) — machine-readable index

## Operating rule

AI เป็น planner/reviewer/worker ไม่ใช่ authority. ทุกการแก้โค้ดต้องมี work identity, base SHA, isolated branch/workspace, verification evidence และสถานะชัดเจน. ห้ามข้าม approval เพียงเพราะ test ผ่าน. ห้ามบันทึก token, API key, credential, cookie หรือข้อมูลลับใน repository
