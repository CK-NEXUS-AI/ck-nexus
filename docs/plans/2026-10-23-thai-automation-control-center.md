# ศูนย์ควบคุม Automation ภาษาไทย — Implementation Plan

> **สำหรับผู้ดำเนินงานอัตโนมัติ:** ดำเนินงานทีละงานตามลำดับ ใช้รายการตรวจสอบด้านล่าง และหยุดที่ review gate หากการทดสอบไม่ผ่านหรือ API จริงไม่รองรับ ห้ามอ้างว่าสำเร็จโดยไม่มีผลตรวจสอบ

**Goal:** เพิ่มศูนย์ควบคุมภาษาไทยที่อ่าน/สร้าง/แก้ไข/ควบคุม Workflow n8n จริง และแสดง execution history โดยไม่เปิดเผย credentials หรือทำลายการเปลี่ยนแปลงเดิม

**Architecture:** คง UI เดิมที่ `creator_app/web/n8n-workflows.html` และ backend gateway ที่ `/usr/local/libexec/cknexus_n8n_workflows_ui.py` ซึ่งให้บริการบน loopback เท่านั้น เพิ่ม endpoint server-side ที่เรียก n8n API หลังตรวจ schema/permissions จริง แยกการสร้างคำสั่งภาษาไทยกับ visual editor ออกจาก API transport เพื่อทดสอบแยกได้ n8n ยังคงเป็น workflow store และ execution engine

**Tech Stack:** Python 3, stdlib HTTP server/urllib (ตาม gateway ปัจจุบัน), HTML/CSS/JavaScript, pytest ตามชุดทดสอบ repo, systemd

## Global Constraints

- รักษาไฟล์เดิมและการเปลี่ยนแปลงที่ยังไม่ commit ทั้งหมด ห้ามใช้ `git reset --hard`, `git checkout --` หรือ `git clean`
- ห้ามเปิดเผย API key, OAuth client secret, access token หรือ refresh token ใน browser, static files, API response, log หรือเอกสาร
- คงการ bind ที่ `127.0.0.1:8791`; ห้ามเปิด public หรือเชื่อมเข้ากับส่วนอื่นของ CK-NEXUS โดยไม่มีการอนุมัติแยก
- อย่าเปลี่ยนแปลงไฟล์ที่ผู้ใช้แก้ไว้ก่อนหน้า เว้นแต่จำเป็นต่อ feature และตรวจ diff ก่อน
- ห้ามสร้าง execution result หรือ workflow status ปลอม; ข้อมูลต้องมาจาก n8n API จริง
- ก่อนเพิ่ม write/run/activate endpoints ให้ตรวจ API schema, version, และ permissions จริง; endpoint ที่พิสูจน์ไม่ได้ให้แสดงว่าไม่รองรับและปิดการกระทำนั้น
- แยกการบันทึกฉบับร่างจากการเปิดใช้งาน; การรันที่อาจส่งข้อมูลภายนอกต้องให้ผู้ใช้ยืนยัน
- ไม่สร้าง OAuth integration จนมี provider client configuration และ redirect URI ที่เจ้าของระบบตั้งค่า
- ไม่ commit เว้นแต่ผู้ใช้อนุมัติอย่างชัดเจน
- แต่ละงานต้องผ่าน focused tests และ integration checks ก่อนดำเนินต่อ

---

## Task 1: ตรวจสอบ n8n API จริงและทำ contract tests

**Files:**
- Create: `tests/test_n8n_workflows_gateway.py` (เสนอ; ตรวจ conventions ก่อนสร้าง)
- Modify: `/usr/local/libexec/cknexus_n8n_workflows_ui.py` เฉพาะเมื่อจำเป็นหลังตรวจ contract; นี่เป็นไฟล์ deploy นอก repo
- Read-only: `/root/.config/n8n/api_key` ใช้เฉพาะใน process; ห้ามพิมพ์ค่า key

**Interfaces:**
- Existing: `GET /api/health`, `GET /api/workflows`
- Proposed internal adapter functions: `n8n_request(method, path, payload=None)`, `list_workflows()`, `get_workflow(workflow_id)`, `list_executions(query)`; ใช้เฉพาะ endpoint ที่ตรวจยืนยันแล้ว
- ผล adapter เป็นข้อมูล JSON ที่ตัด fields ลับออกแล้ว พร้อม error code ที่ไม่เปิดเผยรายละเอียดลับ

- [x] **Step 1: บันทึก baseline และตรวจเอกสาร API**
  - บันทึก `git status --short`, `git diff --stat`, hash และสำเนาสำรองของไฟล์ gateway/UI ที่จะเปลี่ยนไว้ในไดเรกทอรีสำรองนอก Git
  - ตรวจ n8n version/API documentation ที่ติดตั้ง และทดสอบเฉพาะ GET ที่ไม่เปลี่ยน state เพื่อระบุ workflow schema, pagination, executions, node types และสิทธิ์
  - ห้ามพิมพ์ API key หรือ response fields ที่อาจเป็น credentials
- [x] **Step 2: เพิ่ม contract tests ก่อน implementation**
  - ใช้ fake HTTP server/monkeypatch เพื่อทดสอบ 200 JSON, 0 workflows, pagination, timeout, 401/403/404/5xx, malformed JSON และ network error
  - assert ว่า error response ไม่มี key และ raw exception text
- [x] **Step 3: เพิ่ม adapter แยกจาก HTTP handler**
  - กำหนด timeout ชัดเจน, จำกัด path ให้อยู่ภายใต้ `/api/v1/`, ส่ง API key ฝั่ง server เท่านั้น
  - map upstream error เป็นข้อความปลอดภัยและสถานะ HTTP ที่เหมาะสม
  - ปฏิเสธ unsupported endpoint ด้วย 501/ข้อความภาษาไทย โดยไม่ส่ง request ที่ไม่ตรวจสอบแล้ว
- [x] **Step 4: ตรวจ focused tests**
  - Run: `pytest -q tests/test_n8n_workflows_gateway.py`
  - Expected: ทุกกรณี contract ผ่าน และทดสอบว่า secret sentinel ไม่ปรากฏใน body/log
- [x] **Step 5: ตรวจ integration read-only**
  - Run: `curl -fsS --max-time 3 http://127.0.0.1:8791/api/health`
  - Run: `curl -fsS --max-time 10 http://127.0.0.1:8791/api/workflows`
  - Expected: health `ok=true`; workflow list ตรงกับ upstream (ขณะวางแผน upstream ส่ง count 0)


**หลักฐาน/ข้อจำกัด ณ 2026-10-23:** `GET /api/v1/workflows?limit=2` และ `GET /api/v1/executions?limit=2` ตอบ HTTP 200 ด้วย schema `{data, nextCursor}` และรายการว่างจริงทั้งคู่; cursor pagination ผ่าน fake upstream contract test แล้ว แต่ live pagination ยังไม่มีข้อมูลจริงให้ตรวจแบบ end-to-end. `GET /rest/settings` และ `/healthz` แบบไม่ผ่าน auth ตอบ HTTP 403 จึงยังยืนยันเวอร์ชัน n8n ที่ติดตั้งไม่ได้; ไม่อนุมานเวอร์ชันจากเอกสารสาธารณะ. Adapter เปิดเฉพาะ GET สำหรับ `workflows`/`executions`; write/run/activate endpoints ยังไม่รองรับจนกว่าจะตรวจสิทธิ์และ schema จริง. Backup: `/root/cknexus-task1-backup-20261023/`.

## Task 2: ศูนย์ควบคุมภาษาไทยและข้อมูลสถานะจริง

**Files:**
- Modify: `/root/ck-nexus/creator_app/web/n8n-workflows.html`
- Modify: `/usr/local/libexec/cknexus_n8n_workflows_ui.py` เฉพาะ endpoint read-only ที่ Task 1 ยืนยันแล้ว
- Create: `tests/test_n8n_workflows_ui_contract.py` (เสนอ)

**Interfaces:**
- UI เรียก `GET /api/health`, `GET /api/workflows` และ endpoints read-only ที่ Task 1 ยืนยันแล้ว
- UI แสดงสถานะโหลด, ข้อมูลจริง, empty state, error state และ timestamp

- [x] **Step 1: เพิ่ม tests**
  - ตรวจภาษาไทยและเมนูหน้าหลัก/รายการ/ประวัติ/สร้างงาน
  - ทดสอบ render workflow names ที่มี `<script>`, quotes และอักขระภาษาไทยโดยไม่ execute HTML/JS
  - ทดสอบ empty list, upstream error, timeout และการกดรีเฟรชซ้ำ
- [x] **Step 2: ยืนยัน test ล้มเหลวด้วย UI เดิม**
  - Run: `pytest -q tests/test_n8n_workflows_ui_contract.py`
  - Expected: ล้มเฉพาะ assertion ของฟังก์ชันที่ยังไม่มี
- [x] **Step 3: เพิ่มหน้าหลักและ navigation**
  - แยกหน้าหรือส่วน UI สำหรับภาพรวม, สร้างงานภาษาไทย, แผนผัง, งานทั้งหมด, ประวัติ และการเชื่อมต่อ
  - แสดงจำนวน/สถานะจาก API จริงเท่านั้น; ถ้า endpoint ไม่พร้อมแสดง “ยังไม่รองรับ” ไม่ใช้ข้อมูลจำลอง
  - render ข้อมูลที่ไม่น่าเชื่อถือด้วย `textContent`/DOM APIs หรือ escaping ที่ผ่านการทดสอบ; ห้ามใส่ค่าจาก API ลง `innerHTML` โดยตรง
- [x] **Step 4: ตรวจ focused tests**
  - Run: `pytest -q tests/test_n8n_workflows_ui_contract.py`
  - Expected: ทุก assertion ผ่าน
- [x] **Step 5: ตรวจ HTTP และ responsive behavior**
  - ตรวจ `GET /`, `GET /api/health`, `GET /api/workflows` เป็น HTTP 200 ในกรณีปกติ
  - ตรวจผ่าน browser/devtools หรือเครื่องมือที่มีจริงว่าหน้าจอมือถือไม่ล้น และไม่มี secret ใน HTML/JS/network response
  - หากไม่มี browser automation ให้ระบุข้อจำกัดและใช้ static/HTTP checks โดยไม่กล่าวอ้างว่าทดสอบ browser แล้ว


**หลักฐาน/ข้อจำกัด ณ 2026-10-23:** รอบ Red ของ `tests/test_n8n_workflows_ui_contract.py` แสดง 4 failing assertions ที่ตรงกับฟังก์ชันขาดหาย; หลังปรับ UI focused suite `tests/test_n8n_workflows_ui_contract.py tests/test_n8n_workflows_gateway.py` ผ่าน `18 passed`. `node --check /tmp/cknexus-ui-task2.js` ผ่าน (script สกัดจาก HTML); `git diff --check` ผ่าน. หลัง restart `cknexus-n8n-workflows-ui.service` เป็น `active`, listener ยังจำกัด `127.0.0.1:8791`; `GET /` HTTP 200 (15794 bytes), `/api/health` HTTP 200 และ `/api/workflows` HTTP 200 (count 0 จาก upstream จริง). ตรวจ served HTML/JSON ไม่พบ API key หรือ sentinel secret. ไม่มี Playwright/Selenium ติดตั้ง จึงไม่ได้อ้างว่าทดสอบ browser/device จริง; responsive behavior ตรวจจาก CSS media query และ static/HTTP checks เท่านั้น. Backup: `/root/cknexus-task2-backup-20261023/`.

## Task 3: ตัวสร้าง Workflow จากภาษาไทยและบันทึกฉบับร่าง

**Files:**
- Create: `creator_app/web/n8n-workflow-builder.js` (เสนอ; แยก logic ที่ทดสอบได้)
- Modify: `creator_app/web/n8n-workflows.html`
- Modify: `/usr/local/libexec/cknexus_n8n_workflows_ui.py` สำหรับ create/get endpoints ที่ยืนยันแล้ว
- Create: `tests/test_n8n_workflow_builder.py` (เสนอ)

**Interfaces:**
- Proposed: `POST /api/workflows/draft` รับ `{name, description, template_id, parameters}` ตาม schema ที่กำหนดหลังตรวจ API
- Proposed: `POST /api/workflows` รับ workflow JSON ที่ผ่าน validation เท่านั้น หาก n8n ใช้ endpoint/schema อื่นให้ปรับตามหลักฐานจริง
- Builder ส่งออก workflow draft + รายการสิ่งที่ขาด/บริการและ credentials ที่จำเป็น; ไม่เปิดใช้งานอัตโนมัติ

- [ ] **Step 1: เพิ่ม tests สำหรับแผนภาษาไทย**
  - ตรวจ template แบบกำหนดตารางเวลา/เริ่มด้วย manual trigger/ลำดับ node ที่รองรับ
  - ตรวจคำสั่งว่าง, template ที่ไม่รู้จัก, parameter ขาด, node ที่ไม่รองรับ และข้อความที่มีอักขระพิเศษ
  - ตรวจว่าคำสั่งที่ไม่ตรง template ไม่ถูกอ้างว่า AI แปลงสำเร็จ
- [ ] **Step 2: รัน tests ให้เห็น failure**
  - Run: `pytest -q tests/test_n8n_workflow_builder.py`
- [ ] **Step 3: สร้างตัวแปลงแบบปลอดภัย**
  - เริ่มจาก template/intent mapping ที่ระบุชัด; ตรวจ trigger, node type, connections และ parameters
  - ถ้า LLM provider ยังไม่พร้อม ให้เสนอ template/form fallback เป็นภาษาไทย
  - แสดง preview และความเสี่ยงก่อนส่ง create request
  - บันทึกเป็น draft/inactive เท่านั้น; ห้ามผูก credentials โดยอัตโนมัติ
- [ ] **Step 4: ตรวจ focused tests**
  - Run: `pytest -q tests/test_n8n_workflow_builder.py`
  - Expected: valid template produce schema ที่ผ่าน validation; invalid inputs ถูกปฏิเสธอย่างชัดเจน
- [ ] **Step 5: ทดสอบกับ n8n จริงอย่างปลอดภัย**
  - สร้าง workflow ทดสอบชื่อเฉพาะที่ไม่ชนงานเดิมและไม่มี side-effect/credential
  - อ่านกลับและยืนยัน nodes/connections/name; ลบเฉพาะ workflow ทดสอบที่สร้างในขั้นตอนนี้หลังตรวจ ID และยืนยันว่าไม่ได้ active
  - หากสร้างหรือลบไม่ได้ด้วยสิทธิ์ API ให้หยุดและรายงาน blocker โดยไม่ลอง endpoint แบบเดาสุ่ม

## Task 4: Visual Workflow Editor, control actions, history และ security hardening

**Files:**
- Create: `creator_app/web/n8n-workflow-editor.js` (เสนอ)
- Modify: `creator_app/web/n8n-workflows.html`
- Modify: `/usr/local/libexec/cknexus_n8n_workflows_ui.py`
- Create: `tests/test_n8n_workflow_editor_contract.py` (เสนอ)

**Interfaces:**
- Editor ใช้ workflow JSON ที่ `GET /api/workflows/{id}` ส่งกลับและ serialize เฉพาะ schema ที่รองรับ
- Control endpoints ใช้ method/path/payload ตาม API จริงที่ตรวจแล้ว; ห้ามสมมติว่า `activate`, `deactivate` หรือ `execute` endpoint มีอยู่
- History UI ใช้ executions endpoint จริงที่มีสิทธิ์ใช้งาน

- [ ] **Step 1: เพิ่ม round-trip/security tests**
  - workflow ที่มีหลาย nodes/connections, node parameters ที่ไม่รองรับ, missing node IDs, invalid edges, duplicate IDs และ unknown node types
  - เปลี่ยน node/connection แล้ว serialize/deserialize โดยไม่สูญเสีย fields ที่รองรับ
  - malformed JSON, oversized payload, unknown workflow ID, unsupported method, repeated action และ XSS strings
- [ ] **Step 2: ยืนยัน failure**
  - Run: `pytest -q tests/test_n8n_workflow_editor_contract.py`
- [ ] **Step 3: สร้าง editor และ control layer**
  - แสดง node cards/เส้นเชื่อม พร้อมเพิ่ม/ลบ/เชื่อม/แก้ไขเฉพาะ node types ที่รองรับ
  - แสดง unsaved state; ยืนยันก่อนทิ้งการแก้ไข; ปฏิเสธการบันทึกหากมี unknown fields/nodes ที่ editor จะทำให้สูญหาย
  - เปิด/หยุด/ทดลองรันหลังผู้ใช้ยืนยันและหลัง API support ผ่านการตรวจสอบเท่านั้น; disable ปุ่มเมื่อ request กำลังดำเนินการ
  - execution history แสดงเฉพาะข้อมูลที่ API ส่งกลับจริง; ถ้าไม่มีสิทธิ์แสดงคำอธิบายและไม่สร้าง mock data
  - คง loopback binding, ป้องกัน CSRF/origin mismatch, จำกัด JSON size, ตรวจ workflow ID และไม่เปิด CORS กว้าง
- [ ] **Step 4: ตรวจ focused tests**
  - Run: `pytest -q tests/test_n8n_workflow_editor_contract.py`
  - Expected: round-trip ของ schema ที่รองรับผ่าน; schema ที่ไม่รองรับถูกปฏิเสธก่อน save; control action ไม่ยิงซ้ำ
- [ ] **Step 5: regression และ service checks**
  - Run: `pytest -q tests/test_n8n_workflows_gateway.py tests/test_n8n_workflows_ui_contract.py tests/test_n8n_workflow_builder.py tests/test_n8n_workflow_editor_contract.py`
  - ตรวจ `systemctl is-active cknexus-n8n-workflows-ui.service`
  - ตรวจ health/UI/API หลัง restart เฉพาะเมื่อจำเป็น; ถ้าต้อง restart ให้ตรวจ syntax, สำรองไฟล์ และมี rollback copy ก่อน
  - ตรวจ `git status --short` และ `git diff --check`; review diff เฉพาะไฟล์ของงานนี้
- [ ] **Step 6: รายงานผลโดยใช้หลักฐาน**
  - แยก PASS/FAIL/BLOCKED พร้อมคำสั่งและผลจริง
  - ระบุข้อจำกัด เช่น OAuth ยังไม่พร้อม, API permissions ไม่พอ, ไม่มี workflow/credentials หรือ browser automation ไม่พร้อม
  - ไม่ commit โดยไม่มีการอนุมัติแยก

---

## นโยบายการ rollback และการรักษางานเดิม

ก่อนเปลี่ยนไฟล์แต่ละชุด: เก็บ `git status --short`, สำรองไฟล์เป้าหมายแบบมี timestamp นอก repo, ตรวจ hash และ diff ปัจจุบัน จากนั้นแก้เฉพาะไฟล์ที่ระบุใน task นั้น ห้าม restore ทั้ง repository

ถ้า test หรือ health check หลัง deploy ไม่ผ่าน: หยุดขั้นตอนถัดไป, ตรวจ log โดยกรอง secrets, คืนเฉพาะไฟล์ที่ task นี้แก้จากสำเนาที่สร้างไว้, restart service เมื่อจำเป็น แล้วทดสอบ health/UI/API อีกครั้ง หาก rollback ไม่ผ่านให้คง service state ที่ปลอดภัยและรายงานสถานะจริง

## ข้อสรุปที่ยังขึ้นกับหลักฐานจากระบบจริง

- n8n version, endpoint/schema/permissions สำหรับ create/update/activate/deactivate/execute/history
- node types ที่เปิดให้ใช้ใน editor และ fields ที่ editor สามารถรักษา round-trip ได้โดยไม่สูญเสียข้อมูล
- มี LLM provider พร้อมใช้สำหรับแปลงภาษาธรรมชาติหรือควรใช้ template fallback เท่านั้น
- วิธีเปิด UI ผ่าน SSH tunnel/reverse proxy และ browser automation ที่มีอยู่จริง
- OAuth providers ที่จะรองรับก่อน โดยต้องมี client ID/secret และ redirect URI จากผู้ดูแลก่อนเริ่มตั้งค่า
