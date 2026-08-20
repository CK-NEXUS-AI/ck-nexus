# CK_v1 / CK_v2 / CK_v3 Coordination Runtime V1

Status: development architecture only. CK-NEXUS remains the sole authority for state, memory,
permissions, policy, execution, and production status.

## Roles

- **CK_v1 — Primary Cognitive Governor:** interprets the user goal, chooses the plan, reconciles live
  evidence, and makes the final development decision subject to CK-NEXUS policy.
- **CK_v2 — Independent Verifier/Challenger:** checks assumptions, runtime behavior, tests, security,
  provenance, and dissent. CK_v2 reports candidate facts; it cannot self-promote a result.
- **CK_v3 — Bounded Execution Planner/Evidence Synthesizer:** turns a verified CK_v1 decision into a
  constrained work packet, performs or coordinates permitted development work, and returns an
  evidence-ready candidate report. CK_v3 has no policy, credential, merge, deploy, or production
  authority.

## Flow

```text
USER
  -> CK_v1 plan/decision
  -> CK_v2 independent challenge/verification
  -> CK_v1 reconciliation
  -> CK-NEXUS policy gate
  -> CK_v3 bounded work packet
  -> CK_v3 deterministic plan
  -> short-lived CK-NEXUS execution grant
  -> authoritative grant verification + replay guard
  -> bounded read-only adapter
  -> CK-owned read-only tool runtime
  -> CK_v3 candidate report
  -> CK_v2/independent evidence check
  -> CK_v1 reconciliation
  -> CK-NEXUS state/evidence
```

## Fail-closed rules

`creator_app.ai_team.ck_coordination` provides structural controls:

1. helper tasks cannot be assigned production mutation authority;
2. helper tasks cannot be assigned credential-access authority;
3. helper tasks cannot be assigned external-write/deploy authority;
4. reports must match the assigned task ID and role;
5. source-bound tasks reject reports from another/stale source commit;
6. `PASS_CANDIDATE` remains `DONE_CANDIDATE` until independent evidence is verified;
7. any unresolved risk keeps the report in candidate state;
8. helper `FAIL`/`BLOCKED` states are preserved rather than being rewritten as success.

## CK_v3 default boundary

The helper packet builder automatically records these denied actions:

- production mutation;
- credential access/export;
- external write/deploy;
- policy or permission override;
- merge of protected production closure work.

## CK_v3 execution planner

`creator_app.ai_team.ck_v3_planner` converts an already policy-valid CK_v3 work packet into a
deterministic, evidence-first `CKV3ExecutionPlan`. The planner itself does not execute anything.

Additional planner invariants:

- exact 40-hex source commit is mandatory;
- every planned step remains read-only by default;
- every step carries the packet's expected evidence contract;
- the plan explicitly has `execution_authority=False`;
- independent verification is always required;
- textual attempts to place production deployment, credential export/access, external writes, PR #14
  merge, or policy/permission override into `allowed_actions` fail closed.

A plan is not a capability grant.

## CK_v3 read-only execution adapter

`creator_app.ai_team.ck_v3_executor` is the first intentionally narrow adapter that may consume a
policy-valid CK_v3 plan. It still does not grant CK_v3 authority. Execution requires a separate,
short-lived `CKV3ExecutionGrant` supplied by CK-NEXUS and an injected CK-owned tool invoker.

The grant is bound to:

- task ID;
- exact source commit;
- exact source tree;
- exact runtime registry SHA-256;
- an explicit subset of the canonical six read-only device-bridge tools;
- issue and expiry times, with a maximum lifetime of ten minutes.

A grant object is not trusted merely because it is structurally valid. Before any tool invocation,
the adapter requires an `ExecutionGrantVerifier` backed by an authoritative CK-NEXUS broker/store.
A fabricated, missing, rejected, or unverifiable grant fails closed. The adapter also requires an
`ExecutionReplayGuard` to consume each `(grant_id, request_id)` once; replay is denied before a tool
call. Governance verifier and replay-guard operations are bounded by short timeouts.

Before a call reaches the injected runtime, the adapter rechecks the current source commit, source
tree, and runtime registry digest against the verified grant. Drift fails closed before invocation.
Plan actions must use the explicit `tool:<name>` form; natural-language actions cannot become tool
execution implicitly.

The adapter additionally enforces:

- only the canonical six CK-owned read-only tools can appear in a grant;
- a tool must appear in both the plan and the short-lived grant;
- credential, external-write, and production-mutation flags are always false;
- each invocation requires a bounded request ID and one-time replay consumption;
- JSON tool arguments are bounded to 8 KiB;
- sensitive argument keys such as authorization, access/refresh tokens, password, secret, private
  key, client secret, cookie, and API key are rejected recursively before invocation;
- CK-owned tool calls have a bounded execution timeout;
- JSON tool results are bounded to 16 KiB;
- oversized or non-serializable results fail closed and are not returned as raw content;
- runtime exceptions are converted to a bounded generic failure without traceback or secret detail;
- evidence records include request/task/grant/step/tool and source/tree/registry identity plus
  argument digest, result digest, result size, duration, and status, but exclude raw tool arguments.

This adapter is development-only and read-only. It does not create a daemon, queue consumer, public
endpoint, credential source, filesystem mutation path, shell execution path, deployment mechanism, or
production capability. A future command bus consumer must still pass every task through the same
packet, planner, authoritative grant verification, replay guard, runtime-identity, and
independent-verification gates.

## Coordination bus

GitHub Issue #80 is currently the append-only coordination bus for CK_v1/CK_v2/CK_v3 development
reports. Comments are evidence inputs, not authority. Newer exact GitHub/runtime evidence supersedes
stale comments.

Posting a command to the bus does not prove a CK_v2 or CK_v3 worker is online. Live connectivity is
accepted only after an independently observable ACK/report from an actual worker session. A future
automatic consumer must authenticate its worker identity, bind work to the exact source/runtime
identity, and preserve the fail-closed execution-grant boundary above.

## Production boundary

This coordination runtime does not satisfy Q10, Q11, or Q12. It does not modify PR #14 and does not
change Production NO-GO status.