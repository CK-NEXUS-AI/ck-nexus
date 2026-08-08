# CK-NEXUS Full System Web Demo R1

เปิดหน้า `/demo` เพื่อใช้ Control Center แบบเต็มระบบ โดยหน้าเดิม `/` ยังคงเป็น Creator Workspace เดิม

## Quick start — Safe Demo Mode

```bash
export CKNEXUS_MOCK_AI=true
export CKNEXUS_EMAIL_GATEWAY_ENABLED=true
export CKNEXUS_EMAIL_WEBHOOK_TOKEN=demo-webhook-token
export CKNEXUS_EMAIL_DATABASE_PATH=data/email-demo.db
uvicorn main:app --host 127.0.0.1 --port 8000
```

เปิด `http://127.0.0.1:8000/demo`

ใน SYSTEM → SECURE TOKENS ใส่ Email Webhook Token เป็น `demo-webhook-token` แล้วกด Save.

## สิ่งที่ทดสอบได้จาก UI

- Runtime status / health
- Creator Agents + history
- Deterministic email routing
- Atomic email ingest + duplicate detection
- Loop prevention
- Attachment scan/quarantine
- Transactional outbox enqueue/claim/sent
- Lease recovery trigger
- End-to-end audit trace
- Prometheus metrics
- ปุ่ม RUN FULL CYCLE รัน flow อัตโนมัติครบวงจร

## Live Mode

ตั้ง `OPENAI_API_KEY` และปิด `CKNEXUS_MOCK_AI`. สำหรับ PostgreSQL ให้ตั้ง `CKNEXUS_DATABASE_URL` และ `CKNEXUS_EMAIL_DATABASE_URL` ตาม deployment config.

หน้าเว็บไม่ทำให้ provider/n8n staging evidence กลายเป็น Production PASS โดยอัตโนมัติ; provider step ใน Safe Demo ใช้ simulated provider receipt หลัง outbox claim.
