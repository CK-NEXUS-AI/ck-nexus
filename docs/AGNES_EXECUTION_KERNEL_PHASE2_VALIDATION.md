# AGNES Execution Kernel Phase 2 — Validation

Status: **Development Candidate / RC / NO-GO**.

## Implemented

- Linux namespace + chroot sandbox runner.
- Workspace baseline extraction from an exact Git commit.
- Sandbox path/symlink/patch/command guards.
- Process-group timeout kill.
- Resource/output limits.
- Durable single-host SQLite idempotency.
- `hands.code_patch`, `hands.test`, and `hands.security_scan` adapters.
- AGNES execute + approval APIs.
- Sandbox remains disabled by default.

## Local evidence

- Phase 2 targeted: 11 PASS.
- Phase 1 + Phase 2 + AGNES + R9–R11 canonical: 67 PASS.
- Non-billing regression: 162 PASS.
- Full suite: 168 PASS / 3 environment errors (`aiosqlite` unavailable).
- Namespace doctor: PASS (`host_visible=False`, `network=blocked`).
- Wheel build/install sandbox smoke: PASS.
- Wheel SHA-256: `12fe18b2655e3bb1f21f0b17af5cdabef7a7b8ce65bb833962276e9d6c2395db`.

## Explicit blockers / non-claims

- No Docker/bwrap backend in this environment.
- No seccomp profile evidence.
- No cgroup v2 enforcement evidence.
- SQLite idempotency is not distributed and not production-safe.
- No PostgreSQL/Redis production idempotency proof.
- No cloud workspace execution proof.
- No auto-merge or production deploy.
- R12 production evidence remains mandatory.
