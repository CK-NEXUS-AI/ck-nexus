# Autonomous Development Platform V2 Architecture

## Target lifecycle

```text
request
  -> work identity
  -> repository baseline
  -> connector schema verification
  -> bounded task graph
  -> isolated workspace/branch
  -> AI patch worker
  -> AGNES execution kernel
  -> tests + lint + dependency + secret gates
  -> evidence ledger + candidate artifact
  -> draft PR
  -> required CI
  -> review/approval
  -> squash merge
  -> staging gate
  -> production gate
```

## State machine

`RECEIVED -> PLANNED -> WORKSPACE_READY -> PATCHED -> VERIFIED -> CANDIDATE_READY -> PR_OPEN -> CI_GREEN -> AWAITING_APPROVAL -> MERGED -> STAGED`

Failure states are explicit: `BLOCKED`, `DISCARDED`, `CANCELLED`. A plan is never an execution approval.

## Design rules

- ต่อของเดิม ไม่สร้าง orchestrator ซ้ำ
- `ControlPlaneOrchestrator` ทำ planning/dispatch; AGNES ทำ execution
- worker ไม่มี production authority และเรียก external tool ผ่าน `ConnectorFabric` เท่านั้น
- ทุก tool ต้อง discovery, schema hash, risk label และ authorization ก่อน expose
- ทุก patch ต้องผูก base SHA, work_id, branch และ evidence
- AutoGitOps ทำได้เฉพาะ verified commit/push ที่ path อยู่ใน allowlist; ไม่ merge, force-push หรือ deploy
- production ต้องมี staging evidence, distributed idempotency, rollback และ approval แยก

## Main data objects

- `WorkIdentity`: work_id, repository, base_sha, branch, environment, risk, capabilities, idempotency_key
- `TaskGraph`: nodes, dependencies, role, candidate workers, state
- `ConnectorBinding`: connector_id, protocol, schema_hash, risk, mode, approval_ref
- `CandidateArtifact`: diff_hash, changed_paths, test_results, security_results, evidence_refs, requires_merge_approval
- `AutomationRun`: trigger/event, owner, scope, schedule, action, failure_policy, rollback, enabled

## First implementation slice

สร้าง models/state transition tests ก่อน แล้วเชื่อม read-only GitHub baseline เข้ากับ control plane. ยังไม่เปิด n8n write, VPS mutation หรือ production automation
