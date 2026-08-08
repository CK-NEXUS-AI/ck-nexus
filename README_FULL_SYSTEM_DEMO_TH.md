# CK-NEXUS Full System Web Demo R1

เว็บไซต์ทดลองระบบเต็มแบบ browser-based ที่ต่อกับ FastAPI API จริงของ CK-NEXUS

## เปิดใช้งาน

```bash
cd CK-NEXUS-v0.2.0-FULL-SYSTEM-WEB-DEMO-R1
./start_full_system_demo.sh
```

จากนั้นเปิด:

`http://127.0.0.1:8000/demo`

ไปที่ **SYSTEM → SECURE TOKENS** แล้วใส่ Email Webhook Token:

`demo-webhook-token`

กด **RUN FULL CYCLE** เพื่อรัน flow อัตโนมัติครบ:

Health → Creator Agent → Routing → Atomic Ingest → Duplicate Replay → Outbox → Worker Claim/Sent → Audit → Metrics

## หน้าที่มี

- `/demo` — Full System Control Center ใหม่
- `/` — Creator Workspace เดิม
- `/docs` — FastAPI API docs
- `/health` — health check
- `/metrics` — Prometheus metrics

## Safe Demo vs Live

Safe Demo ตั้ง `CKNEXUS_MOCK_AI=true` และใช้ SQLite เพื่อให้เปิดได้ทันทีโดยไม่ต้องมี API key หรือ VPS

Live สามารถเปลี่ยนเป็น OpenAI/PostgreSQL โดยตั้ง environment variables ตาม `.env.prod.example` และ deployment docs โดยไม่ต้องแก้หน้าเว็บ

## สถานะหลักฐาน

หน้าเว็บและ API flow ถูกทดสอบจริง แต่ provider delivery ใน Safe Demo เป็น simulated boundary และ n8n staging/live OpenAI ยังไม่ถูกใช้เป็นหลักฐาน Production P0 PASS


## GitHub Auto Connect

ตั้ง `GITHUB_TOKEN` และ `GITHUB_REPO=owner/repository` ใน environment ของเครื่อง/VPS แล้วเปิดหน้า `/demo` → SYSTEM → TEST GITHUB ระบบจะตรวจ authentication และ repository access อัตโนมัติโดยไม่ส่ง token ไปเก็บใน browser
