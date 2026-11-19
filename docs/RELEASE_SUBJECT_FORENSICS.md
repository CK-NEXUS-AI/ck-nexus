# CK-NEXUS Release Subject Forensics

**Snapshot:** 2026-11-10 UTC
**Repository:** `CK-NEXUS-AI/ck-nexus`
**Purpose:** establish the exact release-subject algorithm and distinguish the current mainline from the frozen Q10-Q16 closure branch.

## Executive finding

The observed SHA difference is a branch/release-line divergence, not evidence that SHA-256 is nondeterministic.

| Git ref | Commit | Tree | Runtime subject |
|---|---|---|---|
| Current remote `main` | `4d1366cef3cbdd18aa174bdf67308567635c750a` | `57adfe86cd6d9bdbca5c97d336cb733df2308ae5` | `10113cb5874edbaeee2c444e0a8a002f3f68dd7ff6fbd1a72a5b6634a0415227` |
| Current remote `release/q10-q16-closure` | `acda4055047b79d3c9e6ee1175c69fafcae49dc0` | `4d3c3758eaa8b8822582f6b5a1a8c2b55ae7ab1f` | `96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f` |

The frozen value `96dcd0f0...` is correct for the existing closure branch. It is not the runtime subject of current `main`. The final production package workflow is scoped to pushes on `release/q10-q16-closure`, so its expected value must not be changed merely to match main.

Current main commit `4d1366c` is the 2026-11-05 homepage unification commit (#358). The closure branch has a materially different runtime tree. Releasing current main requires a new/rebased release candidate and fresh subject-bound evidence; it must not reuse the old closure evidence.

## Canonical algorithm

The runtime subject is the SHA-256 digest of the exact byte stream emitted by:

```bash
git ls-tree -r <commit> -- \
  app creator_app services gateway orchestration idea_engine migrations \
  deploy observability Dockerfile docker-compose.prod.yml main.py pyproject.toml uv.lock
```

This includes tracked Git tree metadata (mode, object type, object ID, and path). It does not hash working-tree file contents directly and does not include untracked or uncommitted changes.

A second, distinct application evidence scope is used by Q05/Q08/Q09:

```bash
git ls-tree -r <commit> -- \
  creator_app services tests scripts main.py pyproject.toml uv.lock
```

These two scopes are not interchangeable. The new `scripts/release_subject.py` preserves both existing byte-for-byte algorithms, reports commit/tree/entry count and calculator digest, and supports an explicit expected-subject comparison. It never rewrites an expected value.

## Evidence and stale references

On current remote main `4d1366c`:

- `RELEASE_STATUS.md` still identifies canonical main as `22edd1f...`; that is not the current remote main SHA.
- The Q10 evidence file records source SHA `4cf17cd...`, release subject `96dcd0f...`, and `gate_result=NOT_VERIFIED`.
- The Q10 scan request remains `PREPARED_NOT_EXECUTED` for source `ad2fac7...` and subject `772662ac...`.
- Q11 is `BLOCKED`; Q12 is marked `PASS`; Q13/Q15/Q16 are `PASS_CANDIDATE`; Q14 is `PASS`; runtime licenses are `PASS`. These committed records are bound to `96dcd0f...`, not current main `10113cb...`, and therefore cannot establish current-main gate status.
- The production decision remains **NO-GO**. No gate is promoted by this forensic report.

The legacy Q11/Q12 final-subject workflows and historical runbooks remain pinned to their old source/subject pair. They are intentionally not rewritten as part of this calculator refactor.

## Repository state and environment

- No `PROJECT_STATE.md` exists in the inspected VPS worktree or in the current main tracked file list. `RELEASE_STATUS.md`, `docs/RELEASE_CHECKLIST.md`, and `docs/Q10_Q16_CLOSURE_CONTRACT.md` are present.
- The VPS is running Ubuntu 24.04.5 LTS, uptime approximately 21 days at inspection.
- VPS root disk was 95% used (about 2.1 GiB free); available RAM was about 540 MiB. Large builds, dependency installs, and cleanup were deliberately avoided.
- The VPS worktree remains on `feature/autonomous-brain-foundation` at `9a6d8f2a05bf412940389e7c6084cac1140fec40`, ahead by one commit, with two pre-existing untracked files. Those files and the worktree were not modified.
- Termux SSH to the last-known VPS IP reached the SSH service but the available key was rejected (`Permission denied (publickey)`). The registered VPS Remote Commander device was separately reachable and confirmed the machine is running. Provider billing/expiry date is not exposed by the guest OS, so active billing cannot be proven from this check.

## Required release decision

1. Keep `96dcd0f...` frozen for the current closure branch; do not replace it with `10113cb...`.
2. Treat current main runtime subject as `10113cb...` for new mainline evidence.
3. If the release candidate is to include current main, create a new release candidate from the exact main SHA, then regenerate Q10-Q16 evidence on that exact source/tree/subject.
4. Do not change the production decision, evidence statuses, or merge any release branch based on subject calculation alone.

## Calculator verification on Termux

The new calculator was run against three independent committed refs with frozen expected values:

- Current main `4d1366c`: `10113cb...` — matched (exit 0).
- Current closure branch `acda405`: `96dcd0f...` — matched (exit 0).
- Historical Q10/Q12 source `ad2fac7`: `772662ac...` — matched (exit 0).

The final suite contains 14 tests, including a linked-Git-worktree regression because the Q10 evidence workflow calculates the target subject from a separate worktree. All 14 tests passed on Termux Python 3.13; compileall and git diff --check also passed.
