# Next AI Handoff

## First actions

1. Read this folder in the order in `README.md`.
2. Run `git status --short --branch`, `git log -1 --oneline`, `git diff --check`.
3. Check whether PR #320 is merged; if not, inspect its required checks without bypassing protection.
4. Inspect current branch and do not mix the pre-existing `final_handoff_artifacts/` or architecture report unless explicitly requested.
5. Re-discover connector availability with `manus-config connector list` and GitHub tool inventory.

## Next coding milestone

Implement P0 contracts only:

- `WorkIdentity`
- `ConnectorBinding`
- `CandidateArtifact`
- `AutomationRun`
- explicit state transition validator
- redaction and idempotency tests
- read-only GitHub baseline adapter

Expected result: deterministic planning and evidence report with no remote mutation.

## Stop conditions

Stop and report `BLOCKED` if:

- base SHA changed unexpectedly
- connector schema cannot be verified
- tool risk is unknown
- credentials are missing or would need to be printed
- test/security/evidence gate fails
- requested action requires merge, production, VPS mutation or trigger creation without explicit policy approval

## Handoff format

Every future completion note must include:

```text
work_id:
repository:
base_sha:
branch:
changed_paths:
tests:
security:
evidence_refs:
remote_actions:
remaining_blockers:
next_step:
```
