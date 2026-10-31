# CK-NEXUS Implementation Backlog จาก Image Scan

วันที่: 2026-10-31
แหล่งที่มา: ภาพอ้างอิง 104 รายการ + synthesis แบบ 10 หมวด
หลักการ: ทำทีละชั้น, reuse โมดูลเดิม, free-first, fail-closed, no auto-production

## P0 — Foundation และ safety boundary

### P0.1 Durable WorkflowRun

ขยาย `ControlPlaneOrchestrator` ให้มี state machine แบบ durable: `created`, `planned`, `validating`, `waiting_for_approval`, `executing`, `verifying`, `succeeded`, `failed`, `rolled_back`, `cancelled`, `expired`.

Acceptance criteria: transition guard, optimistic concurrency, checkpoint/resume, timeout, cancellation, bounded retry, reason code และ audit event ครบทุก transition.

### P0.2 Execution/Event Envelope

กำหนด schema กลางสำหรับ orchestrator, AGNES, ConnectorFabric, GitHub integration และ AutoGitOps: run/workflow ID, correlation/causation ID, actor, tenant/resource scope, capability list, policy snapshot, deadline, budget, sensitivity และ schema version.

Acceptance criteria: schema validation, missing-field rejection, version pin ต่อ run และ no secrets ใน payload.

### P0.3 Fail-closed policy checkpoint

เพิ่ม policy decision point ก่อนทุก connector call และทุก mutation ผลต้องเป็น `allow`, `deny` หรือ `needs_approval` พร้อม policy version, reason และ evidence reference.

Acceptance criteria: agent เปลี่ยน policy ไม่ได้, scope drift บังคับ revalidation, protected branch/production/infrastructure ต้องมี approval.

### P0.4 Connector capability manifests

ยกระดับ `ConnectorFabric` ให้ connector ทุกตัวประกาศ operation, input/output schema, resource selector, permission, risk, timeout, retry class, idempotency, compensation, rate limit, health และ owner.

Acceptance criteria: undeclared operation ถูกปฏิเสธ, contract tests ผ่าน, discovery แสดง capability ที่ใช้ได้จริง.

### P0.5 AGNES sandbox profiles

แยก execution profile อย่างน้อย read-only analysis, branch workspace, test/build และ privileged deployment พร้อม file/network/process/resource limits, cancellation, kill switch และ redacted structured logs.

Acceptance criteria: denied capability ถูกบล็อก, quota ถูกบังคับ, timeout/cancel ทำงาน, logs ไม่เปิดเผย secret.

## P1 — Controlled delivery

### P1.1 Idempotency และ postcondition

สร้าง registry/inbox สำหรับ side effect: branch, PR, issue, connector call, AGNES run และ deployment. ทุก operation ต้องใช้ idempotency key และตรวจผลลัพธ์หลังทำ.

### P1.2 PR-centered golden paths

ทำ versioned templates สำหรับ repository onboarding, PR validation, preview environment, promotion และ rollback โดยสร้าง plan/diff/evidence ก่อน mutation.

### P1.3 Declarative GitOps reconciliation

ให้ AutoGitOps แยก desired/observed state, ตรวจ drift, สร้าง read-only plan และ remediation proposal. Conflict/manual emergency change ต้อง freeze และส่ง review.

### P1.4 Immutable artifact promotion

ผูก commit, artifact digest, SBOM, provenance, signature, tests, target environment และ known-good rollback target. Build ครั้งเดียว, promote artifact เดิม.

### P1.5 Unified run console

แสดงสถานะ, policy, approval, cost estimate/actual, connector calls, diff, evidence, drift, failure reason และ next safe action ด้วย correlation ID เดียว.

### P1.6 Risk-based approval

Approval ต้องผูกกับ hash ของ plan/diff/manifest/digest, มี owner, expiry และ dual control สำหรับ production, privilege และ infrastructure.

## P2 — Reliability, observability และ learning

### P2.1 Progressive delivery

รองรับ staged/canary/blue-green พร้อม metric contract, baseline, soak window, missing-data policy, pause, bounded blast radius และ deterministic rollback.

### P2.2 Incident automation แบบ proposal-first

สร้าง signal normalization, runbook catalog และ flow detect → triage → diagnose → propose → approve → execute → verify → learn. AGNES เริ่ม read-only.

### P2.3 Queue, tenancy และ budget governance

เพิ่ม per-tenant/resource authorization, fair scheduling, concurrency caps, backpressure, token/time/compute/API budgets, soft warning และ hard stop.

### P2.4 Evaluation/replay harness

เก็บ prompt/task/policy/model version, test rubric, evidence และ outcome. Replay ได้เฉพาะ simulation/projection rebuild ที่ไม่ทำ side effect.

### P2.5 Knowledge graph และ controlled memory

สร้าง graph จาก repository → commit → PR → workflow → artifact → environment พร้อม provenance, freshness, confidence, authorization และ controlled write gate.

## P3 — Optional extensions หลังมีหลักฐาน

- Dynamic multi-agent planner เฉพาะ use case ที่มี parallelism/specialization ชัดเจน
- Advisory model/tool routing เพื่อช่วยลด cost โดยไม่มีสิทธิ์เปลี่ยน policy
- Federated external knowledge adapters ผ่าน ConnectorFabric
- Adaptive rollout หลังมี telemetry และ rollback drill เพียงพอ
- Extension SDK และ local contract-test harness สำหรับ platform teams

## Definition of Done สำหรับทุก item

1. มี issue/work identity และ base SHA ชัดเจน.
2. ทำงานบน isolated branch/workspace.
3. มี unit/contract/integration tests ตาม scope.
4. มี security scan และ secret-redaction check.
5. มี evidence bundle และ rollback/recovery plan.
6. ผ่าน policy และ approval ที่เหมาะกับ risk tier.
7. ทดสอบ staging ก่อน production.
8. ไม่มีการ push secret และไม่มี auto-production โดยปริยาย.

## ลำดับรอบถัดไปที่แนะนำ

`P0.1 → P0.2 → P0.3 → P0.4 → P0.5 → P1.1 → P1.2 → P1.3 → P1.4 → P1.5 → P2.1 → P2.2`

ห้ามเริ่ม P3 ก่อน P0–P2 ที่เกี่ยวข้องมี evidence และ operational owner.