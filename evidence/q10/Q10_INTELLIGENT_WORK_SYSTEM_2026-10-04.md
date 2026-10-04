# Q10 INTELLIGENT WORK SYSTEM — Multi-Agent Design (2026-10-04)
## ระบบการทำงานอัจฉริยะที่ได้จาก Multi-Agent Debate (5 บทบาท)

| Metadata | ค่า |
|---|---|
| operator | SOMCHOK N. (Lead AI Developer / Prompt Engineer) |
| repo | spinlnw10-art/ck-nexus |
| head_sha | ba6eac66ac4efab2afff5bb9463d5ffd7a6fef76 |
| date | 2026-10-04 |
| method | Multi-Agent Design Session (Architect / Security / EvidenceVerifier / Scout / Builder) |
| status | SYSTEM DESIGNED — ยังไม่รัน scan (VPS pending) |

---

## 1. สรุปฉันทามติจาก 5 บทบาท (Consensus)

ทุกบทบาทเห็นพ้องกัน 5 ข้อ:

1. **Q10 FULL = BLOCKED** — L5 (Codex Security) เป็น research preview ไม่มี free → ปิดเต็มไม่ได้
2. **Q10 PARTIAL (L1–L4) = ยังไม่ "ได้มา"** — ยังไม่มี scan ที่ HEAD `ba6eac66` → ต้องรันใหม่ทั้งหมด
3. **หลักฐานเดิม (pip-audit ที่ 4cf17cd3) ใช้ไม่ได้** — commit drift ทำให้เป็นหลักฐานเก่า (stale)
4. **ห้ามปน evidence class** — SCA ≠ SAST ≠ Secret ≠ Config ≠ native Codex (แก้ปัญหาที่เจอ)
5. **ต้องเปลี่ยนชื่อ L1–L5 → EG-1..EG-5** — เพื่อไม่ชนกับระดับ ASVS L1/L2/L3

---

## 2. ข้อเสนอที่แต่ละบทบาทให้ (Debate Highlights)

### 🏗️ Architect
- เสนอสถาปัตยกรรม: **Commit Freezer → pinned runner → EG-1..EG-4 scans → Normalizer → Gate Evaluator → Evidence Bundle → Review/Attest → Partial Close / L5 Handoff**
- บทบาทย่อย: Q10 Architect, Evidence Engineer, Security Reviewer, Release Gatekeeper, Standards Mapper, Codex Liaison, VPS/Infra
- เตือน: "partial close" ต้องไม่กลายเป็นคำสวยหรูของ fake closure

### 🛡️ Security
- L1–L4 เป็น **detection taxonomy** ไม่ใช่ closure proof — จะเป็น evidence ได้ต้อง: commit-pinned + reproducible + triaged + reviewed + tied to remediation
- L5 ยังไม่เป็น evidence-grade → ต้องมี signed waiver ถ้าจะยอมรับ

### 🔍 Evidence Verifier
- **เปลี่ยนชื่อ L1–L5 → EG-1..EG-5** (Evidence Gate) เพื่อไม่ชนกับ ASVS
- ต้อง freeze HEAD: `git rev-parse HEAD` + tree hash + `git status --porcelain`
- ต้อง rerun ทุก layer ที่ HEAD — ห้าม reuse หลักฐานเก่า
- **EG-1..EG-4 ไม่สามารถปิด EG-5 ได้** (non-substitution rule)

### 🧭 Scout
- เครื่องมือฟรีเพิ่มเติมที่ยังไม่คิดถึง: **OSV-Scanner, Syft+Grype, Dependabot (ฟรีสำหรับ private repo), Checkov, Hadolint, Dockle, Lynis, ssh-audit, testssl.sh**
- มาตรฐานเสริม: OpenSSF Scorecard, SLSA, CycloneDX/SPDX, VEX, CISA KEV, CVSS/EPSS
- ติดตั้งแบบ non-root: `pipx` + `~/.local/bin` (ไม่ต้อง sudo)

### 🛠️ Builder
- แผนเล็กสุดที่ปลอดภัย: รัน scan ที่ exact SHA, เก็บ evidence manifest ต่อ layer พร้อม SHA256
- Ruff = lint ไม่ใช่ Q10 evidence (ต้องแยก)
- CodeQL ไม่ใช่ทาง (private repo)

---

## 3. ระบบการทำงานอัจฉริยะ (Intelligent Work System) — สังเคราะห์

### 3.1 โครงสร้าง Evidence Gate (EG-1..EG-5)

| Gate | Evidence Class | เครื่องมือ (ฟรี) | มาตรฐานอ้างอิง | สถานะ |
|---|---|---|---|---|
| **EG-1** | SCA (Dependency) | pip-audit, Trivy fs, OSV-Scanner, Syft+Grype | NIST SSDF PW.4 | 🟡 ต้องรันใหม่ที่ HEAD |
| **EG-2** | SAST (Static Code) | Semgrep CE, Bandit | NIST SSDF PW.7 | 🟡 ต้องรันใหม่ที่ HEAD |
| **EG-3** | Secret Detection | gitleaks, Trivy secret | NIST SSDF PS.2 | 🟡 ต้องรันใหม่ที่ HEAD |
| **EG-4** | Config/IaC | Trivy config, Checkov, Hadolint | NIST SSDF PW.6 | 🟡 ต้องรันใหม่ที่ HEAD |
| **EG-5** | LLM Deep Scan | Codex Security | — (complement SAST) | 🔴 BLOCKED (research preview) |

### 3.2 Pipeline อัตโนมัติ (Automated Pipeline)

```
[Commit Freezer] → [Pinned Runner (VPS)] → [EG-1 SCA] → [EG-2 SAST] → [EG-3 Secret] → [EG-4 Config]
        → [Normalizer: รวมผล + SHA256] → [Gate Evaluator: ตรวจ class ไม่ปน] → [Evidence Bundle]
        → [Human Review/Attest] → [PARTIAL CLOSE (EG-1..4)] หรือ [L5 Handoff → BLOCKED]
```

### 3.3 บทบาทในระบบ (Agent Roster)

| บทบาท | หน้าที่ | หยุดเมื่อ |
|---|---|---|
| Q10 Architect | กำหนดเกณฑ์ gate, ตัดสิน close/no-close | เกณฑ์ชัดเจน |
| Evidence Engineer | รัน scans, เก็บ raw artifacts | ทุก layer มี evidence |
| Security Reviewer | triage findings, validate false positives | ทุก finding ถูก triage |
| Release Gatekeeper | บังคับ same-SHA + hash + ไม่ reuse เก่า | ทุก evidence ตรง SHA |
| Standards Mapper | map NIST SSDF / ASVS | mapping ครบ |
| Codex Liaison | ติดตาม L5 access | L5 เปิดหรือ BLOCKED |
| VPS/Infra | runner access, reproducibility | runner พร้อม |

### 3.4 เกณฑ์ผ่าน (Acceptance Criteria) — จาก Evidence Verifier

**PARTIAL CLOSE (EG-1..EG-4) ยอมรับได้เมื่อ:**
- [ ] ทุก scan รันที่ exact SHA `ba6eac66` (ไม่ใช่ commit เก่า)
- [ ] ทุก layer มี raw report + SHA256 + command + exit code + timestamp
- [ ] Evidence class ไม่ปนกัน (SCA ≠ SAST ≠ Secret ≠ Config)
- [ ] มี rationale ว่าทำไม EG-1..4 จึงเป็น compensating controls
- [ ] EG-5 ระบุ BLOCKED อย่างชัดเจน (ไม่ฝืน)
- [ ] มีลายเซ็น + risk owner + expiry date
- [ ] ระบุชัด: **PARTIAL ≠ Q10 DONE ≠ Production**

---

## 4. แผนปฏิบัติทันที (Action Plan)

### ทำได้ตอนนี้ (ไม่มี VPS):
- [x] ออกแบบระบบ (เอกสารนี้)
- [x] วิจัยเครื่องมือ + มาตรฐาน
- [ ] **รอ VPS access** เพื่อรัน EG-1..EG-4

### เมื่อมี VPS access:
1. Freeze HEAD: `git rev-parse HEAD` + tree hash
2. ติดตั้ง non-root: `pipx install semgrep` + `trivy` + `gitleaks` + `osv-scanner`
3. รัน EG-1..EG-4 ที่ `ba6eac66`
4. เก็บ evidence bundle + SHA256
5. Gate Evaluator ตรวจ class ไม่ปน
6. Human review + attest → PARTIAL CLOSE หรือ BLOCKED

### รอเงื่อนไขภายนอก:
- EG-5 (Codex Security) — ติดตาม research preview เปิดให้ใช้

---

## 5. แหล่งข้อมูล (Sources)

- Codex Security: https://developers.openai.com/codex/security · /faq
- NIST SSDF 1.1: https://nvlpubs.nist.gov/nistpubs/specialpublications/nist.sp.800-218.pdf
- OWASP ASVS 5.0: https://owasp.org/www-project-application-security-verification-standard/
- Semgrep CE: https://docs.semgrep.dev/deployment/oss-deployment
- Trivy: https://github.com/aquasecurity/trivy
- OSV-Scanner: https://google.github.io/osv-scanner/
- gitleaks: https://github.com/gitleaks/gitleaks

---

## 6. ลายเซ็น

SOMCHOK N. · Lead AI Developer / Prompt Engineer · 2026-10-04