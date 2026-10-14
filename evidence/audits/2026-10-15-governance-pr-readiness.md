# CK-NEXUS Governance and PR Readiness Follow-up

Date: 2026-10-15 UTC
Scope: GitHub REST/CLI metadata only; no settings, PRs, workflows, permissions, or branches other than this audit-note commit were changed.

## Canonical identity

- Repository: `CK-NEXUS-AI/ck-nexus`
- Main observed during this check: `cb612b72304246781b7dab48dad77d227c40d45d`
- Main tree observed: `20f2073aae91a586619e91bbfd33cc93ab9da872`

## Default-branch governance evidence

- `GET /branches/main/protection` returned HTTP 404 `Branch not protected`.
- One active repository ruleset was found: `Copilot review for default branch` (ID `24928564`), target branch, default branch only. Rules include deletion protection, non-fast-forward protection, and Copilot code review. The ruleset does not declare required status checks or required human approvals.
- Interpretation: GitHub's classic branch-protection endpoint reports no classic protection. The one active ruleset does not itself show CI required-check enforcement or required human approval. Do not claim those controls are enforced based on this evidence.

## PR readiness snapshot

- PR #293: open, non-draft, `mergeable_state=unstable`; CI test/preflight/attack-regression pass, SonarCloud analysis fails.
- PR #294: open draft, `mergeable_state=unstable`; CI test/preflight/attack-regression pass, SonarCloud analysis fails.
- PR #289: open, non-draft, `mergeable_state=unstable`; integration/test/preflight/attack-regression pass, SonarCloud analysis fails. The diff spans many runtime/control-plane/evidence files, so review scope is materially broader than the small #293 provenance change.
- PR #286: open draft, `mergeable_state=blocked`; test and SonarCloud fail.
- None of these PRs was merged or modified in this audit.

## Security alert API interpretation

- Code scanning alerts endpoint returned HTTP 404 `no analysis found`: this is not evidence of a clean scan.
- Secret-scanning and Dependabot alert queries returned zero rows in this snapshot. Endpoint permissions/visibility can affect what the caller can observe; zero rows are not a substitute for a verified scan.

## Recommended order

1. Owner/admin review and configure default-branch governance deliberately: required status checks, required human review, and appropriate bypass policy. This is a recommendation only; no settings were changed.
2. Diagnose SonarCloud analysis failures via an authorized SonarCloud project session; GitHub check summaries/annotations do not expose root cause.
3. Prioritize narrow PR #293 for provenance review; keep #294 draft until scanner least-privilege/evidence binding is reviewed; review #289 as a broad change set; keep #286 blocked until test failure is fixed.
4. Continue Q10–Q16 release gates only with canonical release identity and real evidence.

## Status

- Governance finding: `OBSERVED_GAP_REQUIRES_OWNER_DECISION`.
- PR readiness: `NOT_VERIFIED / NOT_READY_TO_MERGE` based on current checks.
- Production: `NO-GO`.
- This report is an unsigned audit note, not a release attestation.