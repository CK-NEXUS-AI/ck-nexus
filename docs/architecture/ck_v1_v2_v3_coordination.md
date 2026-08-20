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
  -> development execution/tests
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

A future runtime adapter may execute CK_v3 work through the sandbox/execution fabric, but it must map
these structural fields to actual CK-NEXUS policy checks before any tool execution.

## Coordination bus

GitHub Issue #80 is currently the append-only coordination bus for CK_v1/CK_v2/CK_v3 development
reports. Comments are evidence inputs, not authority. Newer exact GitHub/runtime evidence supersedes
stale comments.

## Production boundary

This coordination runtime does not satisfy Q10, Q11, or Q12. It does not modify PR #14 and does not
change Production NO-GO status.
