# AGNES Execution Kernel Phase 2 — Isolated Sandbox Baseline

Baseline: `v0.2.0-r13-agnes-kernel-p1.1` / `8f37036d73e2172fd74dd9687bc2e1264c248fdc`.

## Scope

Phase 2 adds a real local Linux isolation backend for bounded development execution while preserving the Phase-1 security control plane.

The invariant remains:

```text
Agent != Executor
Workspace != Sandbox
```

A workspace becomes executable only through a registered sandbox executor after manifest, capability, permission, approval, credential, audit, and idempotency controls pass.

## Execution path

```text
Plan
→ Validate Skill Manifest
→ Resolve Capability
→ Policy / Permission
→ Sticky Approval Fingerprint
→ Freeze Immutable Execution Manifest
→ Credential Lease
→ Pre-Audit
→ Durable Idempotency Claim
→ Resolve Registered Sandbox Executor
→ Linux user/mount/PID/network namespace
→ chroot with read-only system binds + writable workspace
→ resource limits + process-group ownership
→ Execute
→ Verify
→ Redact
→ Evidence / Append-only Ledger
→ Final Audit
→ Result
```

## Implemented sandbox protections

- User namespace.
- Mount namespace.
- PID namespace.
- Network namespace with no external network path.
- chroot root filesystem.
- `/usr`, `/bin`, `/lib`, `/lib64`, `/opt` bind-mounted read-only.
- Only the selected workspace is writable.
- Temporary filesystem is isolated and `nodev,nosuid,noexec`.
- Command argv allowlist; no caller-provided shell command string.
- Network-capable Git commands such as push/fetch/pull/clone are denied.
- CPU, virtual-memory, process-count, file-size, and open-file limits.
- Output byte ceiling.
- Timeout terminates the entire process group and escalates to SIGKILL.
- Relative path traversal is denied.
- Symlink workspace content is denied.
- Code patches require an explicit path allowlist.
- Phase 2 code patch does not permit file deletion.
- Post-patch workspace diff is revalidated against the allowlist.

## Durable idempotency

Phase 2 adds a SQLite WAL-backed durable idempotency store for **single-host development**. It survives process restart and atomically claims unique execution keys.

It is intentionally marked:

```text
durable       = true
distributed   = false
production_safe = false
```

High-risk staging/production execution still requires a distributed PostgreSQL/Redis implementation.

## Enabled skills

The local namespace executor handles only:

- `hands.code_patch`
- `hands.test`
- `hands.security_scan`

`legs.workspace_open`, cloud workspaces, MCP, provider execution, auto-merge, and production deployment remain outside Phase 2.

## API

Phase 2 adds:

- `POST /api/agnes/execute`
- `POST /api/agnes/approvals`
- existing `GET /api/agnes/execution/status`

The first high-risk request returns `waiting_approval` with the exact sticky fingerprint. Approval is bound to that fingerprint. Any change to input, permissions, workspace, baseline, executor, policy, or credential requirements invalidates it.

## Activation

Sandbox execution is disabled by default.

```env
CKNEXUS_AGNES_SANDBOX_ENABLED=false
CKNEXUS_AGNES_SANDBOX_ROOT=data/agnes-sandbox
CKNEXUS_AGNES_SANDBOX_REPOSITORY_ROOT=/path/to/ck-nexus
```

Run the host capability check before enabling:

```bash
python scripts/agnes_sandbox_doctor.py --repository-root .
```

## Production posture

This backend is **not production-safe yet**. It has real namespace/chroot/resource isolation, but Phase 2 does not claim seccomp/cgroup hardening, distributed idempotency, multi-host evidence, or R12 production evidence.

No auto-merge. No auto-production deploy. R12 remains mandatory.
