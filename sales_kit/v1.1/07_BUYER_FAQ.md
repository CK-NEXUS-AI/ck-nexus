# Buyer FAQ

## Production Ready แล้วหรือยัง?
ยัง รุ่นที่ขายตอนนี้คือ Creator Source Edition — Beta / SELLABLE_SOURCE_BETA และ Q10-Q16 ยังไม่ครบ

## ใช้งานโดยไม่ซื้อ OpenAI API ได้ไหม?
Demo Mode ใช้งานเพื่อทดลอง flow ได้โดยไม่ต้องใช้ OpenAI key ส่วน Live Mode ต้องใช้ credential/provider access ของผู้ซื้อเอง

## ได้ API key หรือ account ของผู้ขายไหม?
ไม่ได้ Package ไม่รวม API keys, OAuth tokens, private keys, credits หรือบัญชีส่วนตัวของผู้ขาย

## เชื่อมบริการภายนอกทั้งหมดมาให้แล้วไหม?
สถานะบัญชี/connector ของผู้ขายไม่ถูกโอนไปกับ source package ผู้ซื้อต้อง authorize บัญชีของตนเองตาม provider terms และ scope ที่ต้องการ

## ใช้งาน AI ฟรีไม่จำกัดไหม?
ไม่รับรอง ค่าใช้บริการ, quota, rate limits และข้อกำหนดของ provider เป็นของแต่ละบริการและบัญชีผู้ซื้อ

## แก้โค้ด/เปลี่ยนแบรนด์ได้ไหม?
ขึ้นอยู่กับ transaction model และสิทธิ์ที่ระบุใน commercial schedule ที่ลงนามจริง

## ได้สิทธิ์ขายต่อไหม?
ไม่ควรสรุปจากตัว source เพียงอย่างเดียว ต้องดูว่า transaction เลือก source assignment หรือ perpetual license และระบุ resale/sublicensing rights ไว้อย่างไร

## มี support กี่วัน?
เฉพาะที่ระบุในใบเสนอราคา/สัญญาจริงเท่านั้น Template ไม่สร้างภาระ support อัตโนมัติ

## รับประกันไม่มี bug/ช่องโหว่ไหม?
ไม่มี software ที่ควรถูกขายด้วยการรับประกันแบบนั้น รุ่นนี้มี automated tests และ security boundaries บางส่วน แต่ Production security qualification ยังไม่ครบ

## ผู้ซื้อจะตรวจว่าไฟล์ตรงกับที่ตกลงได้อย่างไร?
ใช้ release identity และ SHA-256 checksum ที่มากับ Buyer Delivery Package
