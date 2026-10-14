# CK-NEXUS PR CI Follow-up

- Captured at (UTC): 2026-10-14T21:22:00Z
- Repository: https://github.com/CK-NEXUS-AI/ck-nexus
- Current main commit/tree at capture: `cb612b72304246781b7dab48dad77d227c40d45d` / `20f2073aae91a586619e91bbfd33cc93ab9da872`
- Audit branch parent at capture: `02813a6e4edaeb9b89339f13e78d7e4124fed093`
- Method: read-only GitHub CLI/API queries; no PR or workflow was changed or executed.

## PR check evidence

- PR #293 (release evidence source provenance): attack-regression, preflight, and test reported pass. SonarCloud Code Analysis reported fail in the current PR checks. CodeRabbit review completed. PR remains open and unmerged.
- PR #294 (scanner API hardening): attack-regression, preflight, and test reported pass. SonarCloud Code Analysis reported fail. CodeRabbit review was skipped because the PR is draft. PR remains draft/open.
- PR #289 (sandbox runtime/release validation): attack-regression, integration, preflight, and test reported pass; SonarCloud Code Analysis reported fail. PR remains open and unmerged.
- PR #286 (n8n export guard): test reported fail, SonarCloud Code Analysis reported fail, attack-regression and preflight reported pass. PR remains draft/open.
- PR #278 (Q11 capability gates): preflight and test reported fail, SonarCloud Code Analysis reported fail, attack-regression passed. Its base SHA is historical and not current main; reconcile only after reviewing dependency lineage.
- PR #276 (Q12 frozen-subject verification): attack-regression, preflight, and test reported pass; SonarCloud Code Analysis reported fail. GitHub merge metadata previously reported dirty/unmergeable and its base SHA is historical.
- These check results are point-in-time metadata; they do not establish required-check enforcement, merge approval, deployment, or production readiness.

## Scheduled Product Factory failure

- Workflow: `.github/workflows/ai-product-factory.yml`
- Run: [38607704328](https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/38607704328)
- Event: schedule; head SHA: `cb612b72304246781b7dab48dad77d227c40d45d`; conclusion: failure.
- Failed step: `Harvest GitHub signals` at 2026-10-14T17:34:05Z–17:34:06Z.
- The script `scripts/ai_github_harvester.py` invokes `gh api search/repositories` and raises the generic error `github_search_failed` when the command fails. The failed log output was not available in the inspected CLI result, so the precise underlying HTTP/error cause is NOT_VERIFIED. Do not assume the prior GET-method fix is absent or sufficient without the actual failure details.
- Next diagnosis: inspect the raw step logs via GitHub Actions UI/API and capture only sanitized HTTP status/error classification; never print token values. Then add a regression test for the specific failure mode and verify the workflow on a new run.

## Security features

GitHub repository metadata currently reports Code Security, Dependabot security updates, Secret Scanning, and Secret Scanning Push Protection as enabled. The Code Scanning alerts endpoint returned `no analysis found` in a previous query; this does not prove zero vulnerabilities or a successful analysis. Secret-scanning and Dependabot alert queries returned zero items in that response; those counts are only snapshots.

## Decisions

- Do not merge PRs while SonarCloud failures remain unresolved or required-check enforcement is unproven.
- Prioritize PR #293 provenance logic and PR #294 scanner least-privilege review after diagnosing Sonar failures.
- Investigate the scheduled harvester failure from raw logs before changing source code.
- Q10 remains NOT_VERIFIED; Q11 remains BLOCKED/NOT_VERIFIED; Q12 remains NOT_VERIFIED; OpenClaw remains NOT_VERIFIED; production remains NO-GO.

## Integrity interpretation

This report is an unsigned audit note, not a signed release attestation. Executed != verified; a passing subset of checks != merge readiness; zero alert rows != successful security scan; no deployment or runtime verification is implied.
