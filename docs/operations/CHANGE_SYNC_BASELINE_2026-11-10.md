# CK-NEXUS Change Synchronization Baseline — 2026-11-10

**Inspection target:** Termux device `localhost` (Android / Termux)
**Repository:** `CK-NEXUS-AI/ck-nexus`
**Inspection mode:** Read-only inventory before isolated documentation changes
**Canonical product release decision:** NO-GO FOR PRODUCTION

## 1. Canonical repository snapshot

- Local canonical checkout: `~/ck-nexus`
- Base branch: `main`
- Base commit: `4d1366cef3cbdd18aa174bdf67308567635c750a`
- Source tree: `57adfe86cd6d9bdbca5c97d336cb733df2308ae5`
- Initial working tree: clean; `main...origin/main`
- Isolated documentation branch created for this proposal: `docs/change-sync-policy-20261110`
- No push, merge, deployment, or Production promotion performed.

## 2. Worktree inventory findings

The Termux scan found 18 Git metadata roots within the inspected home-directory depth (including one detached-HEAD repository). This is an inventory result, not proof that all possible checkouts outside the scanned depth or excluded cache paths were found.

Important findings:
- `~/ck-nexus`: clean at the inspected base commit `4d1366c...`.
- `~/ck-nexus-fix`: clean at `b82423b...`.
- `~/workspaces/cknexus-q10-q16-rebased-20261105`: clean at `eae1dfe...`.
- `~/cknexus-sentinel`: branch was 7 commits behind its origin tracking branch.
- `~/ck-nexus-ghas-remediation`: branch was 6 commits behind its origin tracking branch.
- `~/cknexus-agnes-memory`: branch `feat/agnes-persistent-ops-memory-20261110`, 3 commits ahead of `origin/main`, with untracked `docs/operations/` and two untracked Agnes bounded-parallel-execution plan/spec files. This checkout was not modified.
- `~/semgrep-rules-q10`: detached HEAD; preserve its state.
- Other discovered checkouts were not modified.

This differs from an earlier inventory that reported `~/ck-nexus` dirty. The current inspection shows it clean; the discrepancy is recorded, not explained away. Confirm that earlier dirty files were preserved in their original checkout or archive before any consolidation or deletion.

## 3. Release documentation discrepancy

The live GitHub `main` branch was independently read as `4d1366cef3cbdd18aa174bdf67308567635c750a` (commit dated 2026-11-05). The repository's `RELEASE_STATUS.md` still identifies an older canonical main commit `22edd1f...` and older Q10 evidence. That Release Status content is stale relative to the inspected main pointer and must be rebaselined from fresh exact-subject evidence.

Do not copy old Q10–Q16 statuses onto the new subject. Do not alter expected hashes to force a match. Until the release subject and every gate are freshly reconciled, retain NO-GO.

## 4. OpenClaw and Termux tooling observations

- `~/oc-final.txt` reports that the expected Ubuntu proot OpenClaw binary path does not exist and the command was not found. OpenClaw is not verified as installed.
- The existing Desktop Commander remote processes were observed; none were terminated or restarted.
- The watcher script passed `bash -n` syntax validation. This does not prove filesystem event detection works.
- No API keys, tokens, private keys, or environment values were read into this report.

## 5. Changes performed in this proposal branch

- Added `docs/operations/CHANGE_SYNC_POLICY.md`.
- Added this baseline record.
- Added a README navigation link to the policy.
- Changes are isolated on `docs/change-sync-policy-20261110`; they are not merged or pushed.
- No runtime, credentials, deployment, Q10–Q16 evidence, or other checkout was changed.

## 6. Required follow-up

1. Review the policy and baseline diff.
2. Confirm earlier dirty `~/ck-nexus` content and partial archive evidence are accounted for.
3. Reconcile `RELEASE_STATUS.md` against the current main source/tree and newly generated exact-subject evidence.
4. Inspect the 18 checkout roots and their worktree relationships before any consolidation.
5. Validate the watcher with a real controlled file event and captured output.
6. Keep Q10–Q16 fail-closed until fresh mandatory evidence and independent review are complete.

**Current result:** policy documentation drafted and locally synchronized on an isolated branch; adoption is pending review and merge. Production remains NO-GO.
