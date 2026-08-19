# CK-NEXUS Universal Credential Broker — สถานะระบบ

## สถานะ: ✅ พร้อมใช้งานแล้ว (Development Branch)

### สิ่งที่จัดการแล้ว

- [x] 🔐 Universal Credential Broker — จัดเก็บ/ดึง/หมุนคีย์อย่างปลอดภัย
- [x] 🔄 LLM Key Pool — สลับคีย์อัตโอโมเติฟเมื่อใช้เกิน 95%
- [x] 🧭 Provider Router — เลือกผู้ให้บริการที่เหมาะสม
- [x] 📧 Gmail OAuth Connector — เชื่อม Gmail ผ่าน OAuth2 (ไม่ขอรหัสผ่าน)
- [x] 🔌 Auto-Connect Manager — ตรวจสอบ/เชือมต่อ/สลับอัตโอโมเติฟ
- [x] 🤖 Free AI Registry — รวม 10+ AI ฟรี (OpenRouter, Groq, Gemini, Claude ฯลฯ)
- [x] 🧪 ทดสอบครบ 19/19 ผ่าน

### โครงสร้างไฟล์

```
creator_app/
├── credentials/                          # ระบบจัดการคีย์และผู้ให้บริการ
│   ├── __init__.py                      # รวมทุกส่วนเข้าเป็นชุดเดียว
│   ├── credential_broker.py             # จัดเก็บ/ดึง/หมุนคีย์ — ปลอดภัย
│   ├── llm_keypool.py                   # พูลคีย์ + สลับอัตโอโมเติฟเมื่อใกล้หมด
│   ├── capability_router.py             # เลือกผู้ให้บริการที่เหมาะสม
│   ├── capability_registry.py           # คลังความสามารถทุกโมเดล
│   ├── free_providers.py                # รายการ AI ฟรี + การตั้งค่า
│   ├── gmail_oauth_connector.py         # เชื่อม Gmail — อ่าน/ส่ง/สกัดข้อมูล
│   ├── gmail_universal_bridge.py        # เชื่อม Gmail กับทุกเว็บ/บริการ
│   ├── ai_provider_manager.py           # ตัวกลางรวมทั้งระบบ
│   └── scripts/
│       ├── get_gmail_token.py           # ตัวช่วยรับ Refresh Token
│       └── dashboard.py                 # แสดงสถานะเชื่อมต่อแบบเรียลไทม์
├── core/
│   └── auto_connect_manager.py          # ระบบเชื่อมต่ออัตโอโมเติฟ
├── tests/
│   ├── test_credential_broker.py
│   ├── test_provider_router.py
│   ├── test_universal_broker.py
│   └── test_keypool_rotation.py
├── .env.example                         # ตัวอย่างการตั้งค่า
└── ai_provider_manager.py               # จุดเริ่มต้น — เรียกใช้ทั้งระบบ
```

### การตั้งค่า

1. คัดลอก `.env.example` ไปเป็น `.env`
2. ใส่ `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` จาก Google Cloud Console
3. รัน `python creator_app/credentials/scripts/get_gmail_token.py` เพื่อขอ Refresh Token
4. ใส่ `API keys` ของ AI providers ใน `.env`
5. รัน `python ai_provider_manager.py start` เพื่อเริ่มระบบ

### คำสั่งใช้งาน

```bash
python ai_provider_manager.py status      # แสดงสถานะ
python ai_provider_manager.py dashboard   # แดชบอร์ดย่อ
python ai_provider_manager.py scan        # สแกนอีเมล Gmail
python ai_provider_manager.py start       # เริ่มทุกระบบ
python ai_provider_manager.py test        # ทดสอบทั้งหมด
```

### การออกแบบระบบความปลอดภัย

- ❌ ไม่เก็บ/พิมพ์/บันทึกคีย์ดิบใดๆ ใน log หรือ state
- ❌ ไม่ขอรหัสผ่าน Gmail โดยตรง — ใช้ OAuth2 เท่านั้น
- ✅ ทุก credential มีผู้ให้บริการ, capability scopes, tenant/account identity, expiry, health state, rate-limit state, cost policy, audit identity
- ✅ Agents/models ไม่ได้รับ credentials โดยไม่จำกัด
- ✅ Fail-closed เมื่อไม่มี provider พร้อมใช้งาน
- ✅ บันทึก audit events เป็น append-only
