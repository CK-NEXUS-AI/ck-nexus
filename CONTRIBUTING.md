# Contributing to CK-NEXUS

## Change control

All changes must be proposed through a pull request. Direct changes to the protected/default branch are not an accepted development workflow.

A pull request must:

1. come from a dedicated branch or isolated worktree;
2. describe the purpose, risk, and rollback path;
3. pass the required CI and security checks;
4. receive at least **one independent human approval** before merge;
5. resolve requested changes before approval;
6. preserve evidence and production-gate boundaries.

Authors and automation must not self-approve their own changes. AI-generated changes are review candidates only.

## Security-sensitive changes

Changes affecting authentication, authorization, credentials, execution, sandboxing, evidence, CI permissions, release signing, or production gates require explicit security review. Secrets must never be committed or pasted into PR logs.

## CK-NEXUS production gates

Development success does not change Q10/Q11/Q12 or production status. A PR, CI pass, scanner result, or machine signature cannot declare a production gate verified.

## Local validation

Run the relevant unit tests, linting, and security checks before opening a PR. Where a change affects a frozen or evidence-bearing subject, test in a separate worktree and record the exact commit/tree and tool versions.
