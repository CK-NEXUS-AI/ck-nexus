# SQLite Hardening Evidence

Repository: `spinlnw10-art/ck-nexus`
Branch: `security/sqlite-hardening-20261117`
Base: `main` at `4d1366cef3cbdd18aa174bdf67308567635c750a`
PR: [#374 — Harden local SQLite database paths and sidecars](https://github.com/spinlnw10-art/ck-nexus/pull/374)

This PR isolates SQLite hardening from the wider integration bundle in PR #373. The candidate now changes **9 files** relative to `main`: four Python modules, two test files, the platform-scope document, and the evidence report/manifest.

## Historical verification on code commit 54510a9

The results in this section were recorded on the prior code commit 54510a991a2b67a58b99976e1a92ade48b284108. They are historical and are not represented as fresh verification of the current revision.

- Full repository pytest suite: **1,008 passed, 2 skipped** (70.54s; exit 0; 12 deprecation warnings).
- Ruff lint check on all six changed Python source/test files: PASS.
- Ruff formatter check: NOT RUN in this verification pass.
- `git diff --check`: PASS.
- Bandit targeted scan on the four changed Python modules: exit 0; no findings reported.
- pip-audit: no known vulnerabilities reported among auditable packages; local package `ck-nexus-creator` could not be audited from PyPI.

## Follow-up verification — code commit `998c80b`

- Targeted VPS tests: **39 passed, 1 warning** across tests/test_brain_runtime.py and tests/capability_fabric/test_ebook_store.py (3.00s) on exact code commit `998c80b`. `defusedxml 0.7.1` was installed only in a temporary test virtual environment under `/tmp`; the system Python environment was not modified.
- Ruff lint: PASS on all six changed Python source/test files on exact code commit `998c80b` (VPS).
- Ruff format check: PASS on all six changed Python source/test files on exact code commit `998c80b` (VPS).
- `git diff --check HEAD^ HEAD`: PASS on commit `998c80b`.
- Full repository pytest suite: NOT RUN TO COMPLETION. The system environment still lacks FastAPI, SQLAlchemy, MCP, Uvicorn, python-dotenv, Pydantic, and httpx; only the two targeted test files were run in the temporary test environment.
- Bandit and pip-audit: NOT RERUN on this revision. Historical outcomes remain in the section above only.

## Review-driven fixes

- For the Brain Journal and Ebook Knowledge Store paths that use `prepare_private_sqlite_parent`, the leaf database parent created by the helper is mode 0700; an existing leaf parent is checked and rejected if non-private, without changing its mode. Ancestors created through `Path.mkdir(parents=True)` retain their normal umask-derived modes. This statement does not cover other SQLite stores such as `IdempotencyStore`, which has separate permission behavior.
- search_readonly() and list_documents_readonly() do not create missing parent directories. The regular search() and list_documents() methods initialize the index and may create directories; directory creation/tightening occurs on the write initialization path.
- Explicit `isolation_level` is forwarded to read-only SQLite connections.
- BrainRuntime and BrainJournal consistently expand `~` journal paths.
- The missing-`O_NOFOLLOW` regression test now works on platforms where the attribute is absent.
- The Q10–Q16 status table links to the [Q10–Q16 Closure Contract](../../../Q10_Q16_CLOSURE_CONTRACT.md).

## Sidecar and TOCTOU boundary

- Regression tests cover symlinked `-journal`, `-shm`, existing `-wal`, and deterministic database-path replacement immediately before `sqlite3.connect`.
- The deterministic path-replacement test confirms detection of that controlled replacement. It is **not** a concurrent TOCTOU stress test.
- Existing sidecars and sidecars visible during connection setup are checked. SQLite may create WAL/SHM later on first use; the private 0700 parent directory is the cross-UID protection boundary for those later creations. Hostile processes running under the same UID remain inside the documented trust boundary.

## Independent review status

Cubic's latest re-review at PR head `46cdd053` identified five issues across six files: directory/file permission wording, report scope, manifest file count, Ruff-format coverage, and the dangling-symlink assertion. The follow-up fixes were committed and pushed as `998c80b`; a new Cubic re-review has not yet appeared. No independent sign-off is claimed. A fresh read-only Codex CLI review of commit `54510a9` reported no actionable defects; it included one speculative P1 note that the reviewer itself qualified as not a direct issue. This review does not replace hosted CI or a new Cubic re-review.

## PR, CI, and release status

| Item | Verified status |
|---|---|
| PR #374 | OPEN |
| Changed files | 9 |
| GitHub Actions | PASS — CK-NEXUS CI, Security Attack Regression, Research Stack Integration, and AI Factory Preflight passed on `998c80b`. SonarCloud Code Analysis is CANCELLED with a generic failed-analysis summary; CodeRabbit was skipped. |
| Cubic re-review | Five issues from review of 46cdd053 addressed in pushed commit 998c80b; re-review pending; no independent sign-off claimed |
| Independent Codex review | COMPLETE — no actionable findings on `54510a9` |
| Required review | BLOCKED — one approval required; zero approvals received; review decision REVIEW_REQUIRED |
| Merge | NOT MERGED — merge state BLOCKED |
| Deployment | NOT DEPLOYED |
| Q10–Q16 | NOT CLOSED / NOT VERIFIED |
| Production readiness | **NO-GO** |

Before the repository transfer, a PR #374 check-run annotation stated: `The job was not started because your account is locked due to a billing issue.` After transfer and push of `998c80b`, four GitHub workflows ran and passed. The personal billing-lock state is not directly visible through the repository API and remains NOT VERIFIED; the earlier lock message no longer prevents these four workflows from running. No alternate GitHub account has been used to bypass it.

PR #373 remains open as a separate, broader 60-file integration bundle. Its SQLite changes overlap the focused PR #374; PR #373 must be reviewed independently and must not be treated as verified by PR #374's test results.
