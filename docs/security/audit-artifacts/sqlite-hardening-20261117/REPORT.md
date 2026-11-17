# CK-NEXUS SQLite and Related Review Evidence

Repository: `spinlnw10-art/ck-nexus`
Branch: `integration/termux-change-sync-policy-20261117`
Base: `main` at `4d1366cef3cbdd18aa174bdf67308567635c750a`
Code commit: `7d820b5ee6b146065b8e7d0f16a6f81febace249`
PR: [#373 — CK-NEXUS integration](https://github.com/spinlnw10-art/ck-nexus/pull/373)

This report covers the SQLite-related source and regression files listed in `manifest.json`. It is not a full review or certification of the complete 63-file PR.

## Current verification on exact code commit

- Focused pytest suite: **117 passed** in 16.45 seconds on exact commit `7d820b5ee6b146065b8e7d0f16a6f81febace249`.
- Ruff check: PASS on all 19 changed Python files.
- Ruff format check: PASS on 17 changed Python files. `creator_app/api.py` and `creator_app/unified_control.py` retain their original formatting; only the FastAPI status-code compatibility literals were changed there.
- `git diff --check`: PASS.
- Workflow YAML parse: PASS for `.github/workflows/universal-system-ci.yml`.

## Review-driven SQLite fixes

- The main database path disappearing during connection setup now fails closed; only SQLite sidecars may legitimately disappear during recovery.
- Explicit `isolation_level` is forwarded for read-only connections.
- The SQLite helper documents the actual sidecar boundary: existing and setup-visible sidecars are checked; WAL/SHM created later are protected by the private database directory across UIDs. Same-UID hostile processes remain inside the documented trust boundary.
- `TaskStore` and `BrainJournal` now use the same private-parent helper. A newly created shared `.state` directory is mode 0700; existing non-private directories are rejected without chmod.
- Read-only Ebook Knowledge Store lookups no longer create missing parent directories.
- `AuthorityStore` uses the hardened SQLite opener; symlinked databases and existing non-private parents fail closed.
- Regression tests cover database unlink during connect, read-only isolation level, shared TaskStore/BrainJournal state permissions, symlink rejection, and no-side-effect read-only lookup.

## Related review fixes in this PR

- OMNI and n8n now share one direct HTTP transport helper that ignores environment proxies and refuses redirects.
- OMNI URLs with literal trailing `?` or `#` delimiters are rejected.
- Browser screenshot retention is bounded to 10 caller-owned artifacts and 24 hours; unrelated temporary directories are not removed.
- Browser screenshot tests assert both `chown` calls and the expected caller UID/GID.
- Agent profile tests now validate role-specific content and both inline and multiline tool allowlists.
- FastAPI validation responses use literal HTTP 422 for compatibility across the declared FastAPI version range.
- Change-sync policy uses the canonical `BLOCKED` workflow state and marks minimum change-record fields as mandatory.

## CI and PR status

- On the preceding workflow-fix commit `939aae0c5b562115e3175c4a9bca53da50ef87b2`, all **7/7 GitHub Actions workflows passed**.
- Workflows for the current code commit `7d820b5ee6b146065b8e7d0f16a6f81febace249` were still in progress when this evidence snapshot was prepared.
- PR #373 remains OPEN and unmerged. No deployment or release was performed.

## Historical evidence only

The earlier full repository run of 1,019 passed / 2 skipped, Bandit 0 high / 0 medium / 0 low, pip-audit 0 known vulnerabilities among 84 auditable packages, SQLite `PRAGMA quick_check: ok`, and the active `cknexus-creator.service` observation were recorded on earlier revisions/runtime observations. They were **not rerun on this code commit** and must not be treated as current-release evidence.

## Limitations and blockers

- This is not a full independent review of all 63 files in PR #373.
- Two P1 findings concern files in the previously signed 11-file owner-signoff scope: the portal's displayed subject digest and the evidence-redaction rule. Those files were deliberately preserved. Editing them would invalidate the existing attestation and requires a new explicit owner sign-off for the revised scope.
- Automatic GitOps publishing remains fail-closed. No environment variable or other publish authorization was enabled.
- Q10–Q16 remain NOT CLOSED / NOT VERIFIED. Production readiness remains **NO-GO**.
