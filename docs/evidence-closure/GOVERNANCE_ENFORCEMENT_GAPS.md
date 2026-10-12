# Governance Enforcement Gaps

**Assessment date:** 2026-10-12  
**Scope:** Read-only GitHub metadata check during preparation of the evidence closure package.  
**Decision impact:** Do not treat governance design as enforced until repository settings prove it.

## 1. Observed GitHub branch metadata

The GitHub branch API response for `main` returned:

- Current commit: `cb612b72304246781b7dab48dad77d227c40d45d`
- Current tree: `20f2073aae91a586619e91bbfd33cc93ab9da872`
- Commit verification: `verified=true`, reason `valid`
- Branch protection metadata: `protected=false`
- Protection enabled: `false`
- Required status checks: enforcement level `off`, contexts empty

This is a live read-only API result from 2026-10-12. It proves only the returned repository settings at that time; it does not establish that every other branch or organization-level control is absent.

## 2. Risk

The independent-review charter describes the required separation of duties, but a charter alone does not technically enforce it. With the returned `main` branch metadata showing protection disabled and required checks off, GitHub may not enforce the intended review/check gate at the branch level.

Do not claim that independent approval or CI checks are technically mandatory until the relevant repository and organization rules have been inspected and validated.

## 3. Recommended remediation (owner: repository administrator)

After reviewing the repository's governance requirements, configure and verify an appropriate ruleset or branch protection policy that, as applicable:

1. Requires pull requests for changes to `main`.
2. Requires approval by at least one eligible reviewer who is not the PR author; for security-sensitive changes, require an independent reviewer or designated team.
3. Dismisses stale approvals when new commits are pushed.
4. Requires the defined CI/security checks to complete successfully; a cancelled, missing, or skipped required check must not be treated as pass.
5. Restricts bypass permissions and documents any emergency bypass role and audit requirement.
6. Prevents force pushes and deletion of the protected branch.
7. Requires CODEOWNERS review for security/evidence/governance paths where supported.
8. Retains audit logs and defines who may change rulesets.

Do not apply these settings blindly: confirm existing automation and authorized administrators first. This document does not change repository settings.

## 4. Verification evidence required after remediation

- Screenshot or API response of the effective ruleset/branch protection, including inheritance and bypass actors.
- Test PR showing that missing independent approval is blocked.
- Test PR showing that a required failed/cancelled check blocks merge.
- Test PR showing that a new commit invalidates stale approval where configured.
- Test confirming force-push/deletion restrictions.
- Timestamp, repository/ref, rule identifiers, verifier identity, and immutable evidence digest.
- Independent human reviewer sign-off.

## 5. Current disposition

**OPEN — GOVERNANCE ENFORCEMENT NOT VERIFIED.** Do not represent the charter as an enforced control until the effective GitHub ruleset and negative-path tests are verified. No settings were changed as part of this audit package.
