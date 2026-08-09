# AGNES Execution Kernel Phase 3 — Hardened Sandbox + Autonomous Dev Pipeline

Status: Development Candidate / NO-GO for production.

## Invariants

- Agent != Executor.
- Workspace != Sandbox.
- Network deny-by-default.
- No auto-merge.
- No auto-production deployment.
- Every pipeline stops at CANDIDATE_READY.
- Sticky approval is bound to immutable work identity.
- Failure causes rollback/discard of the isolated workspace.

## Implemented

- Linux namespace + chroot sandbox inherited from Phase 2.
- `no_new_privs` and capability bounding/inheritable/ambient drop through `setpriv`.
- Real seccomp-BPF launcher that denies dangerous syscalls including mount/umount, ptrace,
  bpf, perf_event_open, module loading, reboot, keyring operations, unshare and setns.
- cgroup v2 manager for `cpu.max`, `memory.max`, `pids.max`, optional `io.max`, and process attach.
- Redis and PostgreSQL distributed idempotency adapters behind the existing idempotency protocol.
- WorkspaceLifecycleManager: CREATED -> INITIALIZED -> READY -> RUNNING_PIPELINE -> CANDIDATE -> DISCARDED.
- AutonomousDevController state machine:
  PENDING_APPROVAL -> APPROVED -> WORKSPACE_CREATED -> BASELINE_CHECKED_OUT ->
  CODE_PATCH_APPLIED -> TESTS_EXECUTED -> SECURITY_SCANNED -> DIFF_REVIEWED ->
  EVIDENCE_COLLECTED -> CANDIDATE_READY.
- Automatic rollback/discard on pipeline failure.
- CandidateArtifact with diff, tests, scan, evidence refs, and `requires_merge_approval=true`.
- ExternalWorkspaceAdapter protocol prepared for E2B / Daytona / Codespaces.
- API:
  - POST `/api/agnes/pipeline/start`
  - POST `/api/agnes/pipeline/{id}/advance`
  - GET `/api/agnes/pipeline/{id}`
  - POST `/api/agnes/pipeline/{id}/discard`

## Security posture

The seccomp profile in this phase is a deny-dangerous-syscalls BPF profile, not yet a minimal
allowlist profile. It is materially stronger than Phase 2 but must not be described as a complete
production seccomp policy until staging workload profiling is complete.

cgroup v2 code is implemented and wired to the sandbox process-start hook. In the current validation
runtime `/sys/fs/cgroup` is mounted read-only, therefore live cgroup enforcement is BLOCKED rather
than claimed PASS.

Redis/PostgreSQL adapters are implemented. Multi-instance semantics are tested against a shared fake
Redis-compatible backend, but no live Redis/PostgreSQL service is available in this validation runtime;
live distributed idempotency remains BLOCKED.
