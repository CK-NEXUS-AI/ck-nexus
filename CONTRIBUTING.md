# Contributing to CK-NEXUS

## Change path

All changes must follow this path:

1. Create a dedicated branch or isolated worktree.
2. Make the smallest scoped change needed.
3. Run the relevant tests, linting, and security checks.
4. Record evidence for material security/release changes.
5. Open a **Draft Pull Request**.
6. Wait for CI to complete.
7. Require at least **one independent human reviewer** before merge.
8. Merge only after review approval and required checks pass.

Direct changes to `main` are not part of the approved workflow.

## Review rules

- Authors must not self-approve security, release, Q10, Q11, or Q12 decisions.
- A reviewer must inspect the actual diff and relevant evidence.
- Security-sensitive changes should document impact, rollback, and verification.
- Failed checks must be investigated; they must not be hidden or rewritten to appear successful.

## Secrets

Never commit API keys, passwords, tokens, private keys, recovery codes, or other credentials. Use the repository/platform secret store or a local root-only secret file as appropriate.

## Automation boundary

Automation may create branches, patches, tests, evidence, and Draft PRs. Automation must not:

- merge to `main`;
- deploy production;
- declare Q10/Q11/Q12 verified;
- override evidence or human review;
- weaken security controls to make a check pass.

## Evidence

For material security and release work, record at minimum:

- commit SHA and tree SHA;
- tool name/version;
- timestamp;
- command/result;
- SHA-256 of generated evidence;
- reviewer decision when review occurs.

## Current production boundary

Development work does not change the authoritative production state. Production promotion remains subject to the project's independent verification and owner sign-off gates.
