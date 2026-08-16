# Seller Handover Playbook

## ก่อนรับเงิน
- ยืนยัน buyer legal name / billing details
- เลือก transaction model: assignment หรือ perpetual source license
- กรอกราคา, taxes, support, acceptance period, governing terms ในเอกสารจริง
- ให้ buyer เห็น Known Limitations และ classification ก่อนเซ็น

## ก่อนส่ง source
- ยืนยัน payment condition ตาม commercial schedule
- ใช้ Buyer Package ที่ checksum ตรงกับเอกสารอ้างอิง
- ห้ามเพิ่ม `.env`, API keys, OAuth tokens, private keys หรือ production data
- ส่ง ZIP + `.sha256` + executed commercial schedule

## Acceptance
- buyer ตรวจ SHA-256
- buyer เปิด Buyer/00_READ_ME_FIRST.md
- buyerทำ Quick Start / Demo Mode ตาม checklist
- บันทึก acceptance หรือ defect list ตามช่วงเวลาที่ตกลง

## หลังส่งมอบ
- support เฉพาะขอบเขต/ระยะที่ลงนาม
- feature requests ใหม่ quote แยก
- อย่าให้ seller credentials เพื่อแก้ปัญหา; ให้ buyer สร้าง/authorize ของตนเอง

## Release identity อ้างอิง
Buyer Package v1 SHA-256: `92b9c8dba6b12a3b2588a89031f523caee49101b2fd154f907ca8a4c677d2cfa`
Runtime base: `45fde79c717b09f8675645aa541a5834ebd4f433`
Subject manifest SHA-256: `51718986a19e6d11467a9e9e9ab536392b38c59cd674a5f1a7a656632b4011fe`
