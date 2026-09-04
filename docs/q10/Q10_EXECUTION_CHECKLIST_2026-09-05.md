# Q10 Execution Checklist

Status target: move Q10 from `NOT_VERIFIED` to `READY_FOR_INDEPENDENT_HUMAN_REVIEW`.

## Frozen authority

| Item | Exact value |
| --- | --- |
| Frozen commit | `39f5c1adb9d761ab418cf088ff1f051b1ca731d1` |
| Frozen tree | `0525195934f703a8becf8a39f6397b2411e0bb2e` |
| Current Q10 authority | `NOT_VERIFIED` |
| Hard rule | Development branches/PRs cannot substitute for the frozen subject |

## Phase 0 — Pre-flight

- [ ] VPS online and reachable by authorized control path
- [x] OS measured as Ubuntu 24.04 x86_64
- [x] Docker working
- [x] cgroups v2 present
- [x] `unshare` present
- [x] `bwrap` present
- [x] user namespace allowed
- [ ] persistent control/runner path admitted
- [x] frozen commit/tree manually verified on VPS
- [ ] backup of mutable operational data if required

## Phase 1 — Exact subject

- [x] Frozen repo exists at `/root/ck-nexus-q10-canonical`
- [x] HEAD = `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- [x] tree = `0525195934f703a8becf8a39f6397b2411e0bb2e`
- [x] worktree clean
- [ ] capture fresh `git log -1 --pretty=fuller` in the authoritative run pack

## Phase 2 — Native Codex Security

- [ ] Use authoritative native Codex Security version/policy accepted for Q10
- [ ] Deep scan
- [ ] Entire frozen repository
- [ ] Run to completion without interruption
- [ ] MACHINE_SCAN_COMPLETE or equivalent native completion evidence present

## Phase 3 — Canonical artifacts

Required:
- [ ] `scan-manifest.json`
- [ ] `findings.json`
- [ ] `coverage.json`
- [ ] sealed/final `report.md`

Recommended:
- [ ] SHA-256 for every artifact
- [ ] timestamp and host/runner identity
- [ ] exact frozen commit/tree binding

## Phase 4 — Integrity and chain of custody

- [ ] SHA-256 manifest
- [ ] append-only/tamper-evident storage path
- [ ] operator/time/host record
- [ ] no findings edited to make the result look better

## Phase 5 — Independent HUMAN review

- [ ] Reviewer sees frozen commit/tree
- [ ] Reviewer sees complete artifact pack
- [ ] Reviewer sees exact scan method/tool identity
- [ ] Formal reviewer result recorded

## Phase 6 — Owner HUMAN sign-off

- [ ] Owner reviews evidence + independent review
- [ ] Explicit owner sign-off recorded
- [ ] Q10 changes to VERIFIED only after all above pass
- [ ] Production remains NO-GO until Q11 and Q12 pass

## Forbidden

- development scan as Q10 evidence
- changing findings to make them pass
- AI self-approval
- scanning a different commit/tree
- declaring Q10 verified before human review + owner sign-off

## Current exact state

```
Q10: NOT_VERIFIED
Q11: BLOCKED
Q12: BLOCKED
Production: NO-GO / NOT CERTIFIED
```

Latest exact evidence wins.
