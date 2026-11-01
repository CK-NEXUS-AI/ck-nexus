# CK-NEXUS GitHub Reconciliation and Verified Work Audit

Date: 2026-11-01 (UTC)
Publication branch: `feat/brain-fabric-20261101`
Publication base: `main` at `580555332d4c43829cc7e198425787b31a36f012`
Brain/capability commit: `a0df02999e4564bf58b40016ac8d7192cd787ea6`

## Verified GitHub publication

### PR #340 — merged

- Pull request: https://github.com/CK-NEXUS-AI/ck-nexus/pull/340
- Scope: require a dedicated read-only GitHub token for the development-status collector; remove dependency on broad GitHub CLI credentials; restrict systemd write paths to the data directory.
- GitHub checks: 5/5 SUCCESS (Preflight, CI test, CodeQL JavaScript/TypeScript, attack regression, CodeQL Python).
- Independent local verification on PR head `09fc987f272737329a2be343a28a8847d962a6d9`: 10 focused tests passed; Ruff passed; `systemd-analyze verify` passed for all three modified service units.
- Merge result: squash merge `580555332d4c43829cc7e198425787b31a36f012`, merged 2026-11-01T05:22:31Z.
- No production service restart or credential rotation was performed as part of the merge.

## Brain and capability fabric implementation

- `creator_app/brain/`: one bounded cognitive facade over the existing control-plane planner, knowledge retrieval, capability catalogue and evidence-derived learning.
- `creator_app/capability_fabric/` and `config/capability_catalog.json`: typed capability inventory; discovery status is not execution permission.
- `creator_app/global_knowledge/ebook_*.py`: rights-gated EPUB/text-PDF ingestion and SQLite lexical retrieval.
- MCP exposes six brain tools: status, plan, learning context, observation record, improvement proposal and journal summary.
- Self-reported outcomes remain explicitly unverified; improvement proposals remain candidates; external tool authority remains NONE; no auto-install, auto-merge, production deployment or Q10 promotion is enabled.
- No third-party e-book corpus was imported by this change; the synthetic canary remains revoked.
- Brain planning is plan-only. It does not execute tasks or invoke a model.

### Live VPS MCP verification

- Development MCP service restarted and remained active on loopback port 8765.
- MCP protocol `tools/list`: 28 tools returned; all six brain tools present.
- `cknexus_brain_status`: `ready_for_planning`; 21 capability catalogue records.
- Task queue reports 2 open tasks; this is an observed count, not a claim that they were executed.
- Knowledge store: 1 source record, 0 active sources, 1 revoked synthetic canary; retrieval mode is lexical.
- `cknexus_brain_plan`: 4 nodes, `PLANNED_NOT_EXECUTED`, external mutation authorization false.
- Q10 remains `NOT_VERIFIED`; production remains `NO-GO`.

## Test and quality results on current main base

- Full repository test suite after security remediation: 963 passed, 2 skipped, 12 warnings, 54.76 seconds.
- The sandbox interpreter-alias regression test was made environment-independent: it now creates a temporary symlink to an executable outside trusted roots rather than assuming the host virtualenv resolves to a different Python binary. Focused test: 1 passed.
- Added EPUB parser regression coverage for DTD/external-entity rejection and SQL search regression coverage for injection-shaped input.
- EPUB XML parsing now uses `defusedxml`; it is declared as a direct project dependency and the lockfile passes `uv lock --check`.
- Search SQL is now static; all query terms are passed as JSON-bound parameters through SQLite `json_each`, removing dynamic SQL construction.
- Bandit exact reviewed gate: 0 unreviewed MEDIUM/HIGH findings after remediation of the four new B314/B608 findings.
- Scoped Ruff lint for changed/new Python modules and tests: passed.
- Ruff format check for new brain, capability-fabric, ebook-ingestion and tests modules: passed.
- Full-repository Ruff lint: 0 findings.
- Full-repository Ruff format check: 83 files would be reformatted; 559 already formatted. No broad auto-format was applied.
- `git diff --check`: passed.
- Gitleaks commit-range scan (`origin/main..HEAD`): 0 findings; scoped changed-file scan: 0 findings.
- Full-history scan across repository refs: 13 historical matches in older test fixtures and example/config files. These are inherited historical matches; no finding exists in the new commit range.
- Q10 frozen subject commit and tree were not modified.

## GitHub backlog audit

At the pre-merge audit timestamp, `gh pr list --state open` returned 188 open pull requests:
- 166 draft; 22 non-draft.
- Merge-state distribution: 67 CLEAN, 74 BEHIND, 31 DIRTY, 15 UNSTABLE, 1 BLOCKED.
- 107 targeted `main`; the rest formed dependent PR chains targeting other development branches.
- Only one non-draft PR targeting `main` had CLEAN merge state and all checks successful: PR #340, now merged.
- After merging #340, the observed open PR count was 187; after opening brain-fabric PR #343, the observed count returned to 188.

### High-value prior work requiring separate reconciliation

| PR | Branch / subject | Observed state | Decision |
|---|---|---|---|
| #137 | `dev/agnes-cognitive-fabric-v1` | Draft, DIRTY; 3 checks successful | Review conflicts and rebase; do not merge blindly |
| #117 | `post-p0/agnes-cognitive-foundation-v1` | Draft, BEHIND; 5 success, 1 failure | Reconcile against current main and fix failed check |
| #150 | `post-p0/agnes-knowledge-repository-v1` | Draft, BEHIND; 2 checks successful | Rebase and run full current-main suite |
| #203 | `post-p0/system-skills-harvest-v1` | Draft, BEHIND; 2 checks successful | Rebase and security review before adoption |
| #135 | `post-p0/n8n-development-agent-fabric` | Draft, BEHIND; 3 checks successful | Rebase; verify against current n8n runtime |
| #177 | `post-p0/agnes-learning-consolidator-v1` | Draft, CLEAN to its dependency branch; 3 checks successful | Preserve dependency chain; validate complete chain before main |
| #154 | `post-p0/agnes-frontier-model-governance-v1` | Draft, CLEAN to its dependency branch; 4 checks successful | Preserve dependency chain; validate complete chain before main |
| #193 | `post-p0/agnes-expert-fabric-reconcile-v2` | Draft, CLEAN to its dependency branch; 2 checks successful | Preserve dependency chain; validate complete chain before main |
| #111 | `feat/agnes-idea-experimenter-v1` | Draft, BEHIND; 1 success, 1 failure | Fix failing check before rebase |
| #262 | `feat/adk-graph-execution-adapter` | Draft, BEHIND; 4 failures, 1 cancelled | Do not adopt until failures are resolved |
| #316 | `feature/cknexus-agent-operating-model-20261031` | Non-draft, UNSTABLE; 7 success, 1 failure; base is `fix/p0-ruff-lint` | Resolve base dependency and failed check |
| #321 | `docs/autonomous-platform-knowledge-base-2026-10-31` | Draft, DIRTY; 8 success, 1 failure | Resolve conflicts and failed check |

### Publication state of the brain branch

- The old `feature/autonomous-brain-foundation` branch was 16 commits behind main and had merge conflicts across existing n8n/web/ops files when reconciled. That merge was aborted without altering the branch.
- A clean publication branch `feat/brain-fabric-20261101` was created from the updated main commit after PR #340 merged. Only the bounded brain/capability/knowledge commit was cherry-picked; no force-push or history rewrite was used.
- Branch was pushed as `feat/brain-fabric-20261101` and PR #343 was opened against `main`: https://github.com/CK-NEXUS-AI/ck-nexus/pull/343.
- The first GitHub CI run caught four new Bandit B314/B608 findings in EPUB XML parsing and dynamic search SQL. Those root causes have now been corrected, with DTD/entity and SQL-injection regression tests added. The PR is not merged; the remediation commit and fresh CI run are pending.

## Explicit exclusions

- Do not rewrite or force-push existing branches.
- Do not merge the dependent draft PR chain automatically.
- Do not treat green CI on an old base as proof against current main.
- Do not modify frozen Q10 evidence, claim Q10 PASS, or deploy production as part of this development update.
