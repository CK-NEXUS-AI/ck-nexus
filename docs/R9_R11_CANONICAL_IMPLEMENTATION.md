# CK-NEXUS R9–R11 Canonical Implementation Candidate

Baseline: R8 `ded79e08b930b5a6b733bcc658bfc9615d1b09a8` on `r8-encrypted-vault`.
Canonical source: `CK-NEXUS-CANONICAL-MASTER-SOURCE-R9-R12.md`, revision 1, sections 5–7.

Release posture: **Development Candidate / Release Candidate / NO-GO**.

## R9 implemented

- FastAPI gateway package split into config/auth/identity/correlation/routing/rate-limit/proxy/audit/BFF modules.
- Route registry is service-ID based and rejects arbitrary user-controlled upstreams.
- Raw Authorization/cookies are stripped before the upstream client seam.
- Redirects are never followed by the default proxy client.
- JWT verifier validates issuer/audience and required identity claims.
- Coarse route permissions are enforced before proxy execution.
- Atomic Redis Lua token-bucket implementation uses a shared key across instances.
- No automatic fallback to the old process-local limiter.
- `/health/live` and `/health/ready` are present; readiness can probe the limiter backend.
- Cluster evidence harness emits machine-readable PASS/FAIL/BLOCKED JSON.

## R10 implemented

- Declarative `patterns.json` registry with six canonical versioned patterns.
- Deterministic selector gives high-risk release/security intents priority and routes unknowns to human review.
- Canonical execution state machine with explicit failure/repair/rollback branches.
- Guardrail evaluator checks kill switch, pattern version, allow/deny tools, permission, circuit state, credential scope, approval, timeout and idempotency.
- `ExecutionController` is the only side-effect execution seam and records pattern/version/tool decisions in audit metadata.

## R11 implemented

- Typed idea nodes and 12 canonical edge types.
- Persistent JSON graph prototype with append-style audit history.
- Updates preserve before-state and archive instead of silent overwrite.
- Similarity/dedup linker preserves both nodes and creates `extends` or `alternative_to` edges.
- Lens selector chooses at most three lenses per pass.
- Canonical opportunity score formula is deterministic.
- Proposal packet targets R10 `product_idea_exploration` and always requires human approval.
- Idea Engine explicitly rejects deploy/send/publish/billing/credential-export/approval/release-gate mutation capabilities.

## Local evidence

- Canonical R9–R11 targeted tests: 23 PASS.
- R8 + R9–R11 non-billing regression: 118 PASS after final hardening.
- Full suite: 124 PASS / 3 billing errors; the three errors are blocked by missing `aiosqlite` in this environment.
- R9 real Redis two-instance cluster proof is **BLOCKED** here because the `redis` package / Redis staging service are not available in this sandbox. The harness returns BLOCKED rather than falling back.

## Still not production evidence

R12 remains mandatory. In particular, real multi-instance Redis proof, PostgreSQL concurrency, live OpenAI AI001, n8n route/audit, backup/restore, alert delivery and clean-machine deployment are not replaced by unit tests.
