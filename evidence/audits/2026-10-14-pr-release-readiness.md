# CK-NEXUS PR / Release Readiness Snapshot

- Captured at (UTC): 2026-10-14T21:11:46Z
- Canonical repository: https://github.com/CK-NEXUS-AI/ck-nexus
- Main SHA at capture: `cb612b72304246781b7dab48dad77d227c40d45d`
- Audit branch parent before this report: `9df181a33af45372ef5ee55714c05b0a4e8848d1`
- Method: GitHub REST API metadata queries only. No PR was edited, merged, closed, or marked ready; no branch was rebased.

## Focused PR status

| PR | Scope | State | Draft | Head SHA | Base SHA | Merge metadata |
|---:|---|---|---|---|---|---|
| #294 | Scanner API least privilege and scan evidence source binding | OPEN | yes | `f8d13b0db2dd3e3b63ef08f58b1e4990c4924c80` | `cb612b72304246781b7dab48dad77d227c40d45d` | mergeable=true; mergeable_state=unstable |
| #293 | Release evidence source provenance | OPEN | no | `b7bd83ba6d157dcfe353fa81744c75e7f14b4e13` | `cb612b72304246781b7dab48dad77d227c40d45d` | mergeable=true; mergeable_state=unstable |
| #289 | Sandbox runtime and release validation gaps | OPEN | no | `e7e39ef063e4d6e5ab22649c891d7e7b0992562f` | `cb612b72304246781b7dab48dad77d227c40d45d` | mergeable=true; mergeable_state=unstable |
| #279 | Q11 provider error classification | OPEN | yes | `9e739a2eb83ef4bdbb81973da81021149ef68bc4` | `e40e7417eac8f8cae6f96d956e32b1f66d4d6aad` | mergeable=true; mergeable_state=unstable |
| #278 | Q11 capability sub-gates | OPEN | no | `e40e7417eac8f8cae6f96d956e32b1f66d4d6aad` | `b96049db9ae206bdc2292108629d8583ea0277d6` | mergeable=true; mergeable_state=unstable |
| #276 | Q12 frozen-subject verification | OPEN | no | `1c6d9b0d70c23cdae314e5be0baa6823a04795f7` | `3d4370824d506e14444b7662647258a376ef3153` | mergeable=false; mergeable_state=dirty |
| #275 | CI release-evidence boundary | OPEN | no | `7990ba7005994fcb11798ce4e9a708d400e0cdca` | `3d4370824d506e14444b7662647258a376ef3153` | mergeable=true; mergeable_state=unstable |

## Interpretation

- PR #294, #293, and #289 are based on current main at capture, but GitHub reports `mergeable_state=unstable`; do not infer CI/review readiness from `mergeable=true` alone.
- PR #278 is based on historical main SHA `b96049db9ae206bdc2292108629d8583ea0277d6`, not the current main SHA. It is stale relative to current main until explicitly reconciled.
- PR #276 is reported as dirty/unmergeable and is based on an older base SHA `3d4370824d506e14444b7662647258a376ef3153`. It must not be merged without conflict resolution and re-verification against the current release identity.
- PR #279 targets the Q11 capability branch rather than current main. Preserve that dependency relationship; do not treat it as a direct mainline candidate.
- Existing open PRs are candidate work, not evidence that their changes are merged, deployed, or verified in runtime.

## Recommended sequence

1. Keep all PRs open and unchanged during this evidence-first phase.
2. Review PR #294's scanner least-privilege change against current systemd facts: scanner runs as root and has ProtectSystem/ProtectHome/PrivateTmp disabled in the current unit metadata.
3. Review PR #293's evidence provenance changes against the currently observed main commit/tree and exact-release binding.
4. Review PR #289 and Q12 work against fresh kernel enforcement evidence; the current delegated cgroup has unbounded CPU/memory/PID values.
5. Reconcile stale-base PRs only through a deliberate branch owner workflow, then rerun checks on the exact updated head SHA.
6. Do not merge until human-review and required-check enforcement gaps are resolved and all required checks are stable and proven to run on pull_request events.

## Gate status

This snapshot is metadata-only. It does not prove the contents of the PR changes are correct, that checks passed on current heads, or that changes are deployed. Production remains NO-GO.
