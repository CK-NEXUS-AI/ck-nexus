# CK-NEXUS — System Development Dashboard

> Canonical runtime: `python -m creator_app.unified`
> Compatibility note: `python main.py` and the legacy shell launchers remain available as compatibility entry points, but the repo's canonical app runtime is `creator_app.unified`.
> Production status: `NO-GO` — repository metadata and CI evidence are available, but Q10–Q16 gate execution and independent review remain incomplete.

> **สถานะระบบ:** 🚧 Development / Pre-Production · `production_status = NO-GO` · อัปเดตจากการตรวจ VPS และ Repository วันที่ 2026-11-04
> **หลักฐานสำคัญ:** CK-NEXUS CI / Trusted Verifier Image CI และ Code Quality บน main สำเร็จ; ผลดังกล่าวเป็น CI evidence ไม่ใช่ production certification และไม่ลดระดับ Q10–Q16 ที่ยังคง `NOT_VERIFIED / BLOCKED`.
> **หน้า UI:** เปิด `/development` หลังรัน Creator App เพื่อดูสถานะหลักฐานและแหล่งข้อมูลที่ตรวจยืนยันได้

## ภาพรวมใน 1 นาที

| หมวด | สถานะจริงล่าสุด | หลักฐาน / ข้อจำกัด |
|---|---|---|
| Repository metadata | ✅ Verified | GitHub repo metadata and branch state fetched from GitHub API |
| CI / tests | ✅ Success on main | `CK-NEXUS CI`, `Trusted Verifier Image CI`, `Code Quality: Push on main` completed successfully |
| Security scan | ❌ Not verified | Q10 layered open-source security gate remains `PREPARED_NOT_EXECUTED` / `NOT_VERIFIED` |
| Runtime health | ⚠️ Not independently verified | Local execution not performed in this session; no live runtime evidence claimed |
| Production readiness | 🔒 **NO-GO** | Q10–Q16 evidence remains incomplete; no production claim or release gate pass |

> **เปอร์เซ็นต์ความคืบหน้า:** ยังไม่แสดงตัวเลขรวมเพราะไม่ได้มีหลักฐานขั้นสุดท้ายต่อ Q10–Q16.

## Canonical runtime and compatibility

The repository has multiple startup paths. The canonical runtime for the application is:

```bash
python -m creator_app.unified
```

Compatibility entry points that still exist and remain supported are:

```bash
python main.py
./start.sh
./start_unified.sh
```

These legacy launcher paths are compatibility wrappers. They are not the process that should be used as the documented canonical runtime in onboarding or release documentation.

## แผนผังสถาปัตยกรรม

```text
                    CK-NEXUS PLATFORM
                            |
             +---------------+----------------+
             |                                |
        Control Plane                    MCP / API Layer
    Task Store · Worker · Verify       Gateway · MCP Tools
             |                                |
             +---------------+----------------+
                             |
                  Safety / Execution Gates
           Safe Canary only · Least Privilege
                             |
                 Evidence · Tests · Audit Logs

    Model Studio / Qwen ── pending authenticated inference
    Production Gate     ── NO-GO (locked)
```

## Roadmap ตามลำดับความสำคัญ

1. **P0 — รักษาสถานะและตรวจความต่าง**: เก็บ Git diff/ไฟล์ที่ยังไม่ติดตาม ตรวจ Dependency และเก็บหลักฐาน
2. **P1 — MCP Regression & Deployment**: ตรวจ SDK compatibility, ทดสอบ Auth/Resource/Audience และทำ Canary หลัง Deploy ก่อน Restart บริการ
3. **P2 — Model Studio**: ตรวจ Credential ผ่านช่องทางปลอดภัยและเรียกโมเดลจริงเมื่อได้รับอนุญาต
4. **P3 — Autonomous Workflow**: เพิ่ม Handler ที่ได้รับอนุมัติ, Sandbox และ Dependency-aware dispatch; คงการทำงานไว้ที่ safe frontier
5. **P4 — Production Readiness**: End-to-End, Security Review, Rollback และหลักฐานการทดสอบครบก่อนเปลี่ยน NO-GO

## Safety Gates

- `production_status = NO-GO`
- `external_mutation_authorized = false`
- MCP bind ต้องคงเป็น `127.0.0.1:8765`
- ห้าม Reset/Clean/Merge/Auto-commit งานเดิมโดยไม่ตรวจ diff และเก็บหลักฐาน
- ห้ามแสดง API Key, Token หรือข้อมูลรับรองใน Log/README
- ห้ามอ้างว่า Model Studio ทำงานจริงจนกว่าจะมีผล Inference ที่ยืนยันได้
- No evidence -> no done. Q10–Q16 remains blocked until actual execution and reviewer evidence exists.

## ลิงก์และหลักฐาน

- [Repository บน GitHub](https://github.com/CK-NEXUS-AI/ck-nexus)
- [GitHub Issues](https://github.com/CK-NEXUS-AI/ck-nexus/issues)
- [GitHub Actions](https://github.com/CK-NEXUS-AI/ck-nexus/actions)
- [Execution Ledger / progress.md](progress.md)
- [Project Status](PROJECT_STATUS.md)
- [Release Status](RELEASE_STATUS.md)
- [Q10 Closure Contract](docs/Q10_Q16_CLOSURE_CONTRACT.md)
- [Control Plane tests](tests/)
- [แผนงานและรายงาน](docs/plans/)

---

> สถานะรุ่นนี้: **Creator Edition v0.2.0 candidate** — ใช้งานและทดสอบได้ใน Demo Mode ภายใต้เงื่อนไขไม่ใช่ Production Ready. ความปลอดภัยและ Q10–Q16 ยังต้องผ่านการทดสอบจริงและ review ที่เป็นอิสระก่อนจะมีผลการยืนยันผลิตภัณฑ์.

## เริ่มใช้งานเร็วที่สุด

ต้องมี Python 3.11 ขึ้นไป

```bash
cp .env.example .env.local
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m creator_app.unified
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env.local
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m creator_app.unified
```

เปิด `http://127.0.0.1:8000`

หลังติดตั้ง package แล้วสามารถใช้คำสั่ง `ck-nexus` ได้โดยตรง ระบบจะอ่าน `.env.local` และเริ่มจาก `creator_app.unified` โดยตรง

## เปิด Live Mode

1. บันทึกคีย์ไว้ใน `.env.local` ภายใต้ตัวแปร `OPENAI_API_KEY`
2. เปลี่ยน `CKNEXUS_MOCK_AI=false`
3. เลือกโมเดลผ่าน `OPENAI_MODEL` (ค่าเริ่มต้น `gpt-5.6-sol`)
4. เริ่มเซิร์ฟเวอร์ใหม่

ห้ามใส่คีย์ลงใน source code, commit, screenshot หรือข้อความแชท

## คำสั่งตรวจ Release

```bash
python scripts/release_check.py
```

หรือรันแยก:

```bash
python -m compileall -q creator_app main.py
pytest -q
pip-audit
```

สร้างไฟล์ส่งมอบพร้อม SHA-256 หลัง build package:

```bash
uv build
python scripts/package_release.py
```

`pip-audit` เป็นการตรวจ dependency ที่ติดตั้งอยู่ใน environment ปัจจุบัน จึงควรรันอีกครั้งต่อเมื่อมี environment ที่ตรงกับ subject และมีหลักฐาน full scan เป็นจริง

## API หลัก

- `GET /health` — readiness
- `GET /api/status` — โหมดและสถานะการตั้งค่าแบบไม่เปิดเผย secret
- `GET /api/agents` — agent catalog
- `GET /api/dev-team` — รายชื่อ Development Council 5 ผู้ช่วยและสถานะ readiness
- `POST /api/dev-team/run` — ปรึกษาทีมแบบ auto/full council/focus role โดยไม่มี side effect
- `POST /api/runs` — สร้างผลงาน
- `GET /api/runs` — ประวัติ
- `GET /api/runs/{run_id}` — ผลงานรายรายการ
- `DELETE /api/sessions/{session_id}` — ลบประวัติและ memory ของ session
- `GET /docs` — OpenAPI UI
- `GET /api/integrations/status` — สรุป GitHub / Slack / Google Drive / OpenAI / Database โดยไม่เปิดเผย secret
- `POST /api/integrations/test-all` — ทดสอบ integration ที่ตั้งค่าไว้จากฝั่ง server

## โครงสร้างสำคัญ

```text
creator_app/
  api.py            HTTP API, auth gate, limits, security headers
  catalog.py        Creator Agent catalog และ instructions
  runtime.py        OpenAI Agents SDK / Demo Mode
  unified.py        Canonical runtime entry point
  dev_team.py       Lead Orchestrator + 5 Development Council advisers
  storage.py        Local SQLite history
  web/              หน้าเว็บแบบไม่มี third-party CDN
  docs/             build brief, architecture, prompt และคู่มือผู้ขาย
  tests/            API, storage, auth, rate-limit และ configuration tests
services/billing/  โมดูล SaaS เดิม (optional, ไม่เปิดใช้ใน Creator Edition)
```

## ขอบเขตที่ยังไม่ควรโฆษณาเกินจริง

- ยังไม่ใช่ Enterprise multi-node platform
- ยังไม่มี Telegram, marketplace, billing UI หรือ customer portal ในรุ่นนี้
- ยังไม่มีผล Live API smoke test จนกว่าจะตั้งค่าคีย์ที่ใช้งานได้
- License template ต้องใส่ชื่อผู้ขาย เงื่อนไข support และผ่านการตรวจทางกฎหมายก่อนใช้จริง
- หากเปิดใช้อินเทอร์เน็ตสาธารณะ ควรวางหลัง HTTPS reverse proxy และตั้ง `CKNEXUS_ACCESS_TOKEN`

อ่าน [Release Checklist](docs/RELEASE_CHECKLIST.md) ก่อนออก release จริง ส่วน Commercial License / Seller Checklist อยู่ใน seller package แยกต่างหาก

รายละเอียด Integration Hub อยู่ใน [Integration Hub](docs/INTEGRATION_HUB.md), ทีมผู้ช่วยพัฒนาอยู่ใน [Development Council](docs/DEVELOPMENT_COUNCIL.md), และผลตรวจอยู่ใน [Security Audit](docs/SECURITY_AUDIT.md) และ [Test Report](docs/TEST_REPORT.md)

## เอกสารอ้างอิงทางเทคนิค

Agent runtime ออกแบบตาม [OpenAI Agents SDK guide](https://developers.openai.com/api/docs/guides/agents) และใช้ `Runner.run` พร้อม local session memory ที่ไม่ใช่ production evidence สำหรับ Q10-Q16.

## R7 Credential Broker & Provider Router Cutover

R7 connects the R6 provider-routing primitive to the real CreatorRuntime and Development Council.
The runtime now uses a least-privilege Credential Broker, supports a loopback-only Ollama adapter,
keeps OpenAI behind brokered credentials, and exposes only redacted provider/credential status.
Gmail OAuth and GitHub App authentication are available as development-candidate integrations;
OAuth refresh tokens are ephemeral-memory only in this slice, so production still requires an
encrypted durable vault and the existing P0 staging gates. See
`docs/R7_CREDENTIAL_BROKER_PROVIDER_CUTOVER.md`.

## R9–R11 Canonical Implementation Branch

The `gateway/`, `orchestration/`, and `idea_engine/` packages implement Canonical Master Source
revision 1 sections 5–7 on top of the verified R8 baseline. R9 distributed rate limiting is
implemented with an atomic Redis Lua token bucket and does **not** silently fall back to the
process-local limiter in production. The real two-instance Redis proof remains a staging gate;
local unit tests are not production evidence.

## AGNES Execution Kernel Phase 3

Phase 3 adds a bounded autonomous development pipeline on top of the Phase 1 control plane and Phase 2
isolated sandbox. It adds real seccomp-BPF filtering, no-new-privileges/capability drop, cgroup-v2
integration hooks, distributed Redis/PostgreSQL idempotency adapters, workspace lifecycle, pipeline
state/evidence, and candidate artifacts. The pipeline always stops before merge and production deploy.
See `docs/AGNES_EXECUTION_KERNEL_PHASE3_HARDENED_PIPELINE.md`.

