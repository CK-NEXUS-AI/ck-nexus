# CK-NEXUS Autonomous Completion Fabric

Status: POST-P0 / DEVELOPMENT ONLY / NOT PRODUCTION EVIDENCE

## Objective
Provide an evidence-first automation fabric that lets CK-NEXUS coordinate external execution surfaces while preserving CK-NEXUS as the authority for state, policy, permissions, verification, and production eligibility.

## Authority boundary
External services MAY execute bounded development, test, scan, sandbox, observability, or packaging tasks. They MUST NOT independently promote Q10/Q11/Q12, merge PR #14, deploy production, alter the frozen production subject, or persist raw credentials into repository/evidence.

## Execution surfaces
- GitHub: canonical source, PR/issue/workflow/artifact evidence.
- Codex Security: native deep security scanning for Q10 when run against the exact frozen target.
- Linux/VPS executor (for example SentinelX or an approved self-hosted runner): Q12 delegated cgroup v2 verification and runtime tests.
- Vercel/Replit: non-production preview/demo/e2e surfaces only, with synthetic data and no production credentials.
- Database sandbox: isolated test-only persistence for integration/e2e/load verification.
- Website/agent-readiness scanner: external validation of web-readable metadata/protocol surfaces; results are development evidence unless persisted and independently verified.
- Policy/governance layer: bounded tool permissions, explicit production-deny rules, and audit trail for agent actions.

## State machine
DISCOVERED -> CONNECTED -> AUTHORIZED -> EXECUTED -> VERIFIED -> PERSISTED_EVIDENCE

No state may be skipped. A plugin being installed or connected is not evidence that an action executed or passed.

## Evidence classes
- TRANSIENT_EVIDENCE: chat/tool response, ephemeral MCP result, preview-only signal.
- PERSISTED_EVIDENCE: immutable artifact/report with source identity, run identity, timestamp, digest, and verifier provenance.
- PRODUCTION_GATE_EVIDENCE: persisted evidence satisfying the canonical exact-subject gate contract.

## Autonomous loop
1. Read latest authoritative state.
2. Select only unmet gaps.
3. Plan bounded action and required evidence.
4. Execute in development/sandbox scope.
5. Verify independently.
6. Persist artifact + SHA-256 + provenance.
7. Update tracker with explicit status.
8. Remediate failures on a separate development branch.
9. Re-run affected checks.
10. Stop fail-closed on ambiguity, subject drift, secret exposure, destructive scope, or production mutation request.

## Immutable production constraints
Frozen runtime/security source: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
Frozen tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
PR #14 remains unmerged until canonical closure succeeds.

## Autonomous decision policy
AI may choose tools, test order, remediation branches, documentation structure, and development-only sandbox resources when they do not create paid commitments or production mutation. Human/account-owner action remains required where an OAuth/install/credential provider explicitly requires owner consent or where legal/third-party certification requires an external signer.
