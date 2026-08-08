# AGNES Execution Kernel Phase 1 — Security Baseline

Baseline parent: R13 AGNES Skill Nervous System `4f864ea00d51ce8029629d58ae4f16b8f39257b0`.

Release posture: Development Candidate / LAB / NO-GO for production.

## Locked invariants

1. **Agent != Executor.** AGNES selects/plans capabilities; only registered executors may perform execution.
2. **Workspace != Sandbox.** A directory/workspace is never treated as a security boundary by itself.
3. **Immutable execution manifest.** Before execution, identity/risk/input/workspace/baseline/policy/permissions/credential-requirements are hashed into one immutable manifest.
4. **Sticky approval.** Approval is bound to a fingerprint of skill/version/input/actor/tenant/workspace/baseline/policy/executor/risk/permissions/path scope/credential requirements. Any change invalidates the approval.
5. **Executor risk cannot downgrade skill risk.** Effective risk is the maximum of skill/capability/executor risk.
6. **Credential lease boundary.** Executors receive broker-bound leases; AGNES does not receive a raw bulk secret export. User-sourced secret leases are rejected.
7. **Fail closed.** Missing permission, approval, credential broker, audit, idempotency safety, executor, or verification blocks execution.
8. **Kill switches are hierarchical.** Global, tenant, executor and skill scopes can stop work.
9. **Evidence before promotion.** Sandbox/workspace output cannot become a production artifact directly.
10. **No auto-merge / no auto-production deploy in Phase 1.** `upgrade.self_improve` remains proposal/evidence-only until later governed phases.

## Phase-1 flow

```text
Plan
-> Validate Skill Manifest
-> Resolve Capability
-> Risk Classification
-> Policy
-> Permission
-> Sticky Approval Fingerprint
-> Freeze Immutable Execution Manifest
-> Credential Lease
-> Pre-Audit
-> Idempotency Claim
-> Resolve Registered Executor
-> Isolated Execution (not implemented in Phase 1)
-> Verify Result Identity/Terminal State
-> Redact
-> Evidence
-> Append-only Ledger
-> Final Audit
-> Result
```

## Implemented modules

```text
creator_app/agnes/execution/
  request.py           immutable request + ExecutorType + RiskClass
  result.py            terminal/state enums + result envelope
  manifest.py          immutable execution manifest + hashes
  capabilities.py      capability/executor resolution
  permissions.py       explicit capability permission evaluation
  approval.py          sticky approval fingerprints + TTL grants
  credentials.py       Credential Broker lease adapter
  kill_switch.py       global/tenant/executor/skill switches
  idempotency.py       Phase-1 in-memory claim store (NOT production-safe)
  registry.py          executor registry
  guards.py            risk + policy engine
  verification.py      result identity/terminal-state verification
  evidence.py          redaction + append-only pre/final audit
  promotion.py         candidate->verify->scan->approve->promote model
  dispatcher.py        fail-closed orchestration kernel
  adapters/base.py     executor protocol/context only
```

## Deliberately NOT implemented in Phase 1

- LocalSandboxExecutor / Docker sandbox
- E2B / Daytona / Codespaces live execution adapters
- host shell execution
- durable PostgreSQL/Redis idempotency backend
- auto-merge
- automatic production promotion
- automatic production deployment
- production self-modification

The default executor registry is empty. Therefore an otherwise valid request reaches `no_capable_executor` and is BLOCKED instead of falling back to host execution.

## Artifact promotion

```text
CANDIDATE -> VERIFIED -> SCANNED -> APPROVED -> PROMOTED
        \-> REJECTED at each pre-promotion stage
```

Direct `CANDIDATE -> PROMOTED` is invalid.

## hands.code_patch target state machine

```text
BASELINE_LOCKED
-> WORKSPACE_CREATED
-> PATCH_PROPOSED
-> PATCH_APPLIED
-> COMPILE
-> TEST
-> SECURITY_SCAN
-> DIFF_REVIEW
-> EVIDENCE_COMPLETE
-> WAITING_APPROVAL
-> CANDIDATE_READY

failure -> ROLLBACK / DISCARD_WORKSPACE
```

Phase 1 defines the states but does not yet execute code patches.
