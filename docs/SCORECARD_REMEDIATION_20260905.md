# OpenSSF Scorecard Remediation — 2026-09-05

## Baseline

- Repository: `spinlnw10-art/ck-nexus`
- Baseline OpenSSF Scorecard: **3.4/10**
- Baseline run: 2026-09-05
- This remediation is prepared on branch `security/scorecard-remediation-20260905`.
- No change in this branch changes Q10/Q11/Q12 or production status.

## Changes in this proposal

### Token Permissions

- Keep workflow-level permissions read-only.
- Move `packages: write` from workflow scope to the specific `verify-image` job that publishes to GHCR.
- No `write-all` permission is introduced.

### Pinned Dependencies

Mutable GitHub Action version tags were replaced with the exact commit SHA resolved from the same upstream major tag. This reduces supply-chain drift while preserving the intended action major version.

### SAST

A Semgrep visibility workflow is added.

- Runs on pull requests, pushes to `main`, and manual dispatch.
- Uses pinned Semgrep 1.175.0.
- Uses read-only GitHub token permissions.
- Initial adoption is non-blocking so existing findings can be triaged without hiding the baseline.
- Raw JSON evidence is retained as a workflow artifact.

### Dependency Updates

Dependabot configuration covers:

- Python/pip at repository root
- GitHub Actions
- Docker at root, gateway, and trusted verifier image
- npm integration directories

Updates are proposed as PRs. No auto-merge is configured.

### Security Policy

`SECURITY.md` defines private reporting, response targets, triage, isolated remediation, and the production-gate boundary.

### Human Code Review

`CONTRIBUTING.md` requires PR-based changes, CI, and at least one independent human approval. Automation and PR authors may not self-approve.

### Signed Releases

Cosign v3 signing/verification helpers and a public release-signing key are prepared. The private key and password remain outside the repository with owner-only permissions.

Signed-release enforcement is **not enabled** by this PR and remains subject to human adoption.

## Branch protection / rulesets blocker

On 2026-09-05, both the branch-protection and repository-ruleset GitHub API endpoints returned HTTP 403 with:

`Upgrade to GitHub Pro or make this repository public to enable this feature.`

CK-NEXUS will not make the private repository public and will not purchase a plan automatically. Therefore this item remains:

`BLOCKED_BY_GITHUB_PLAN`

until the owner changes the GitHub plan or chooses another control.

## Required human review before merge

The reviewer should verify:

1. workflow permission changes preserve required GHCR publishing;
2. pinned Action SHAs correspond to the documented upstream major tags;
3. Semgrep CI is intentionally visibility-only during initial adoption;
4. Dependabot coverage matches actual package manifests;
5. release-signing private material is absent from the repository;
6. Q10/Q11/Q12 and Production statuses remain unchanged.

## Authority state

- Q10 = `NOT_VERIFIED`
- Q11 = `BLOCKED`
- Q12 = `BLOCKED`
- Production = `NO-GO / NOT CERTIFIED`

This document is a remediation record, not a certification.
