# CK-NEXUS Change Synchronization and Evidence Update Policy

**Policy ID:** CKN-OPS-CHANGE-SYNC-001
**Status:** Proposed on an isolated documentation branch; not yet merged or adopted by the canonical runtime.
**Authority:** CK-NEXUS Core / L3 Authority
**Default release decision:** NO-GO FOR PRODUCTION

## 1. Purpose and precedence

Every change to CK-NEXUS must be recorded, measured, verified where applicable, and synchronized with the documentation and evidence surfaces it affects. This policy is an operational overlay to the Canonical Runtime Contract and Unified Operations Contract; it does not create a new authority, runtime, product, or workflow state machine.

If this policy conflicts with an existing authority contract, the Core/L3 authority contract and the repository's current canonical contracts take precedence. A documentation proposal does not itself grant runtime permissions or production approval.

## 2. Product identity invariants

- CK-NEXUS is one platform with one canonical application runtime: `python3 -m creator_app.unified`.
- Agnes is the AI orchestration and execution layer, not an independent authority or separate product.
- Creator Workspace is the user-facing workspace.
- `/development` is the internal development and evidence dashboard.
- CK-NEXUS Core / L3 Authority owns state, memory, permissions, policy, approvals, execution decisions, and evidence.
- n8n, MCP, OpenClaw, external agents, and third-party services are adapters/workflow services only; they have no CK-NEXUS policy authority (`authority_level=NONE`).
- External connectivity, code presence, passing test subsets, CI success, or a running service do not establish Production readiness.

## 3. Required change lifecycle

Use the existing Unified Operations Contract workflow states:

`RECEIVED -> PLANNED -> QUEUED -> RUNNING -> MEASURED -> REVIEW_REQUIRED -> COMPLETED`

`BLOCKED` is a fail-closed side state. Do not introduce a competing state machine.

For each change:
1. **Discover:** identify the exact repository, branch, commit, worktree, runtime, configuration, and evidence affected.
2. **Plan:** define scope, reason, expected outcome, risk, rollback/preservation approach, and required approvals.
3. **Authorize:** obtain the applicable Core permission and human approval before consequential mutations.
4. **Implement:** change only the authorized scope; preserve unrelated and untracked work.
5. **Record:** create a change record immediately after the mutation.
6. **Measure:** run relevant tests, scans, health checks, and effect measurements.
7. **Verify:** validate the actual resulting state against the intended outcome; tests alone are not independent verification.
8. **Synchronize:** update affected documentation, registries, status surfaces, and evidence references immediately.
9. **Review:** require independent review where the applicable contract requires it; the implementer cannot self-approve.
10. **Complete:** follow the existing human-review and merge requirements. Development completion never changes Production status automatically.

If any required step cannot be completed, mark the change BLOCKED or synchronization-pending in the appropriate system and state the reason. Never report completion while required evidence or synchronization is missing.

## 4. Immediate synchronization scope

After a change, inspect each affected surface and update it when materially impacted:

- Product identity, unified architecture, and authority boundaries.
- Canonical Runtime Contract, launch instructions, and deployment definitions.
- Component, agent, skill, capability, and tool registries/contracts.
- Permission, policy, approval, and credential-reference records.
- Integration adapters and workflow definitions.
- Repository branch, commit, source tree, changed-file inventory, and review state.
- Runtime/deployment state and redacted status APIs.
- Test, security, verification, audit, and evidence records.
- Development status and the `/development` dashboard / `/api/dev-status` snapshot.
- Release Status, Release Checklist, Q10–Q16 evidence, and delivery manifests when affected.

Do not edit unrelated documents merely to create activity. Record that an unaffected surface was checked when that distinction matters. If a dashboard or authority-owned store cannot be updated, explicitly mark synchronization pending; a local Markdown note is not a substitute for a live Core state update.

## 5. Minimum change record

Every consequential change record should contain:

- `change_id`, UTC timestamp, actor/agent, and assigned scope.
- Authority/permission and approval reference, or an explicit not-required reason.
- Repository, branch, base commit, resulting commit, and source-tree identity where relevant.
- Affected files, components, adapters, and runtime surfaces.
- Reason, expected effect, risk, and preservation/rollback notes.
- Commands or procedures executed, exit codes, and measurement results.
- Verification method, result, and evidence locations/digests.
- Documentation and dashboard synchronization status.
- Unresolved findings, blockers, and reviewer identity/status when required.

Use `UNKNOWN`, `NOT_AVAILABLE`, or `PENDING` for missing data. Never fabricate timestamps, reviewer identities, evidence links, hashes, progress, or results. Never include secret values; use credential references only.

## 6. Repository and runtime safety

Before editing, inspect branch, HEAD, working-tree status, untracked files, exact diff, worktree relationships, and relevant backups/evidence. Do not reset, clean, overwrite, stash, delete, merge, or deploy over existing work without reviewing and preserving it.

Keep repository state, deployed runtime state, test results, and release evidence as separate facts. Reconcile them before deployment. Keep the MCP service loopback-bound at `127.0.0.1:8765` under the current deployment contract. Keep credentials server-side.

## 7. Evidence and release semantics

The following distinctions are mandatory:

- IMPLEMENTED is not VERIFIED.
- MEASURED is not REVIEWED.
- TEST PASS is not Production approval.
- CI PASS is not release approval.
- Hash match alone is not complete verification.
- CONNECTED is not WRITE_AUTHORIZED.
- AUTHORIZED is not EXECUTED.
- EXECUTED is not VERIFIED.
- VERIFIED is not PRODUCTION.
- Historical evidence is not evidence for a different current release subject.

Production remains NO-GO until every mandatory Q10–Q16 gate passes against the exact immutable release identity and required independent reviews are complete. A partial gate pass never promotes the whole gate.

## 8. Synchronization failure handling

If implementation succeeds but one or more required surfaces cannot be synchronized:
- Keep the change in a pending/blocked state in the applicable workflow.
- List each stale surface and the reason it was not updated.
- Preserve the implementation and its evidence; do not silently roll back or overwrite unrelated work.
- Assign the synchronization follow-up.
- Do not report the change as COMPLETED or VERIFIED until the applicable requirements are met.

## 9. Completion rule

A change is complete only when its authorized implementation, required measurements, verification, affected documentation/status synchronization, evidence provenance, and required independent review are all satisfied under the governing contracts.

**Operating principle: Every change is recorded, verified, and synchronized immediately. No evidence, no completion.**
