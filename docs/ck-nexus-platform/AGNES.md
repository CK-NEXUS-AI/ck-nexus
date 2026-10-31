# AGNES Capability and Safety Contract

## Capabilities found in CK-NEXUS

- immutable execution manifest
- risk classification and policy evaluation
- capability and permission resolution
- sticky approval fingerprint
- credential lease service
- kill-switch hierarchy
- idempotency store and replay protection
- append-only ledger and evidence builder
- executor registry and result verifier
- isolated sandbox phases, namespace/process limits, seccomp/cgroup work
- candidate artifact model and rollback/discard path

## Non-negotiable invariants

- Agent != Executor
- Workspace != Sandbox
- network deny-by-default
- no auto-merge
- no auto-production deployment
- every pipeline stops at `CANDIDATE_READY` until approval
- failure discards or rolls back the isolated workspace
- approval is bound to immutable work identity and commit/base SHA

## Current readiness

AGNES Phase 3 เป็น development candidate / `NO-GO` for production. Security profile ยังไม่ใช่ minimal allowlist seccomp policy. ใน validation runtime cgroup v2 mounted read-only และไม่มี live Redis/PostgreSQL distributed idempotency. สิ่งเหล่านี้ต้องทำ staging validation ก่อนเปิด autonomous promotion

## AI usage contract

AI วางแผน วิเคราะห์ เขียน patch ใน workspace และสรุป evidence ได้ แต่ไม่สามารถยกระดับสิทธิ์, อ่าน secret โดยตรง, ข้าม policy, merge เอง หรือสั่ง production deploy เอง
