# PATH B — Alternative Native Security Tool Rationale (2026-10-04)

| Metadata | ค่า |
|---|---|
| operator | SOMCHOK N. (Lead AI Developer / Prompt Engineer) |
| repo | spinlnw10-art/ck-nexus |
| target_sha | ba6eac66ac4efab2afff5bb9463d5ffd7a6fef76 (HEAD ปัจจุบัน) |
| date | 2026-10-04 |
| status | RESEARCH COMPLETE — ยังไม่รัน scan (ต้องรันบน VPS) |

---

## 1. ข้อจำกัดของ Q10 (จากหลักฐานจริง)

- Q10 ต้องการ **native Codex Security evidence** (AI-assisted deep code scan)
- Codex Security เป็น **research preview** — ไม่มีใน Free plan
- หลักฐานเดิม (`Q10_DEPENDENCY_AUDIT.json`) ระบุ `codex_security_deep_scan: REQUIRED_SEPARATELY`
- **repo เป็น private** → ตัวเลือกที่ต้องใช้ public repo ใช้ไม่ได้

---

## 2. ตารางเปรียบเทียบเครื่องมือ (จากแหล่งที่ตรวจสอบได้)

| Tool | ประเภท | ฟรี? | รันบน VPS non-root? | ข้อมูลออกนอกเครื่อง? | ครอบคลุม native code scan? | แหล่ง |
|---|---|---|---|---|---|---|
| **Semgrep CE** | SAST | ✅ ฟรี (LGPL 2.1 OSS) | ✅ CLI `semgrep scan` | ❌ ไม่ส่งข้อมูลออก (local scan) | ✅ SAST (แต่ single-file / single-function taint เท่านั้น) | docs.semgrep.dev |
| **Snyk Code** | SAST | ✅ Free 100 scans/เดือน | ✅ CLI | ⚠️ ส่งโค้ดไปประมวลผลที่ Snyk cloud | ✅ SAST (Python beta) | snyk.io/plans, snyk.io/blog |
| **Trivy** | Multi-scanner | ✅ ฟรี OSS | ✅ CLI | ❌ local | ⚠️ dependency + config + secret — **ไม่ใช่ full code SAST** | github.com/aquasecurity/trivy |
| **CodeQL** | SAST | ⚠️ ฟรีเฉพาะ **public repo** | ต้อง GitHub Actions | ส่งไป GitHub | ✅ SAST | docs.github.com |

---

## 3. ข้อค้นพบสำคัญ (Evidence)

1. **Semgrep CE** — ฟรี, open source (LGPL 2.1), รัน local ได้ ไม่ส่งข้อมูลออกนอกเครื่อง เหมาะกับ private repo บน VPS มากที่สุด แต่ข้อจำกัด: วิเคราะห์ได้แค่ single-file / single-function taint (ไม่ใช่ cross-file deep analysis แบบ Codex)
2. **Snyk Code** — มี Free tier (100 scans/เดือน) แต่ต้องส่งโค้ดไปประมวลผลที่ Snyk cloud → ต้องพิจารณา data privacy
3. **Trivy** — ครอบคลุม dependency (รวม `uv.lock` ที่ ck-nexus ใช้) + config + secret แต่ **ไม่ใช่ native code SAST** → class ยังไม่ตรง
4. **CodeQL** — ฟรีเฉพาะ public repo → **ใช้ไม่ได้** เพราะ ck-nexus เป็น private

---

## 4. ข้อเสนอ (Recommendation)

**เครื่องมือแนะนำ: Semgrep CE** — เป็นตัวเลือกที่ตรง class มากที่สุด (SAST) + ฟรี + รัน local บน VPS non-root + ไม่ส่งข้อมูลออกนอกเครื่อง

**แต่ต้องระบุอย่างซื่อสัตย์:**
- Semgrep CE ≠ Codex Security (AI-assisted deep scan) — เป็น **alternative evidence class**
- ผลลัพธ์ที่ได้น่าจะเป็น **🟡 PARTIAL CLOSE** (มี evidence บางส่วน + ข้อจำกัดชัดเจน) ไม่ใช่ FULL CLOSE
- ต้องมี rationale ว่าทำไมจึงยอมรับเป็น alternative — และต้องไม่แอบเรียกมันว่า "Codex Security PASS"

---

## 5. ขั้นตอนถัดไป (Next Steps)

1. [ ] รัน `semgrep scan --config auto` บน VPS (non-root) ที่ commit `ba6eac66...`
2. [ ] เก็บ raw report (unmodified) + คำนวณ SHA-256
3. [ ] กรอก Evidence Checklist 10 ข้อ
4. [ ] เขียน rationale ว่าทำไม Semgrep CE จึงเทียบเท่า (หรือไม่เทียบเท่า) Codex Security
5. [ ] ตัดสิน verdict: 🟡 PARTIAL / 🔴 NO CLOSE / ⚫ CANNOT CLOSE

---

## 6. แหล่งข้อมูล (Sources)

- Semgrep CE: https://docs.semgrep.dev/deployment/oss-deployment · https://docs.semgrep.dev/semgrep-pro-vs-oss
- Snyk: https://snyk.io/plans/ · https://snyk.io/blog/snyk-code-now-available-free-sast/
- Trivy: https://github.com/aquasecurity/trivy/blob/main/docs/guide/coverage/iac/index.md · .../coverage/language/python.md
- CodeQL/GHAS: https://docs.github.com/en/billing/concepts/product-billing/github-advanced-security

---

## 7. ลายเซ็น

SOMCHOK N. · Lead AI Developer / Prompt Engineer · 2026-10-04