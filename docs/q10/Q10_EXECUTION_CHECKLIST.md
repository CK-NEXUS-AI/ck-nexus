# Q10 Execution Checklist

Status target: `NOT_VERIFIED -> READY_FOR_INDEPENDENT_HUMAN_REVIEW`

Frozen subject:
- commit: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`

Authority:
- Q10: `NOT_VERIFIED`
- Q11: `BLOCKED`
- Q12: `BLOCKED`
- Production: `NO-GO / NOT CERTIFIED`

## Phase 0 — Pre-flight

- [ ] VPS control plane currently online
- [x] Ubuntu 24.04 x86_64 measured on VPS
- [x] Docker daemon measured working
- [x] cgroups v2 measured present
- [x] `unshare -Ur` measured PASS
- [x] `bwrap` installed and basic sandbox measured PASS
- [x] frozen repository present at `/root/ck-nexus-q10-canonical`
- [x] frozen repository HEAD/tree measured exact
- [x] frozen repository working tree measured clean
- [ ] persistent least-privilege control/runner agent admitted
- [ ] optional GitHub self-hosted runner registered/verified if used
- [ ] pre-scan backup decision recorded if needed

Latest control-plane status: Remote Desktop Commander device `10616a96dd5c121bb` is currently OFFLINE. Do not infer VPS failure from this alone.

## Phase 1 — Exact Subject

Required:
- [x] commit `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- [x] tree `0525195934f703a8becf8a39f6397b2411e0bb2e`
- [x] clean worktree measured
- [ ] fresh pre-authoritative-scan identity record captured

Never substitute a development branch, PR, remediation branch, or canonical main for the frozen Q10 subject.

## Phase 2 — Native Codex Security

- [ ] authoritative scanner identity/version approved
- [ ] scanner supply-chain risk decision recorded
- [ ] quota/provider authority available
- [ ] native deep scan started exactly once on frozen subject
- [ ] scan completes without interruption
- [ ] machine completion marker present

Development GitHub Actions scans are supplemental only.

## Phase 3 — Canonical Artifacts

Required:
- [ ] `scan-manifest.json`
- [ ] `findings.json`
- [ ] `coverage.json`
- [ ] sealed/final `report.md`
- [ ] raw logs
- [ ] machine-completion evidence
- [ ] scanner identity/version
- [ ] host/runtime identity
- [ ] subject commit/tree binding

## Phase 4 — Integrity / Chain of Custody

- [ ] SHA-256 for every canonical artifact
- [ ] manifest binds artifact hashes
- [ ] timestamp and runner/host identity recorded
- [ ] previous-hash / ledger link recorded where applicable
- [ ] evidence stored in protected location
- [ ] no post-scan edits to findings/report that alter meaning

## Phase 5 — Darker / Independent Verification

- [ ] fresh Darker verification after canonical scan
- [ ] finalizer/artifact guard PASS
- [ ] review pack generated
- [ ] independent HUMAN reviewer receives exact evidence pack
- [ ] reviewer result recorded without AI self-approval

## Phase 6 — Owner Sign-off

- [ ] Owner HUMAN reviews evidence and reviewer result
- [ ] explicit Owner HUMAN sign-off recorded
- [ ] Q10 authority transition performed only after all gates pass
- [ ] Q11/Q12 remain blocked until their own requirements pass
- [ ] Production remains NO-GO until all required production gates pass

## Forbidden

- development evidence substituted for Q10 evidence
- changing frozen subject/tree
- editing findings to make the result look better
- AI self-approval
- AI acting as independent reviewer
- declaring VERIFIED before human review + owner sign-off
- Production GO before Q11/Q12 closure
- credential/secret disclosure

Latest exact evidence wins.
