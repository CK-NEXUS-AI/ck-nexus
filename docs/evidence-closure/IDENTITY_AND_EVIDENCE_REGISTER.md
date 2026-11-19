# Identity Freeze and Evidence Register

**Assessment date:** 2026-10-12  
**Classification:** Audit working paper; requires independent validation  
**Decision:** Production NO-GO

## 1. Identity Freeze Table

| Identity | Commit | Tree | Signature / status | Permitted use |
|---|---|---|---|---|
| Canonical Candidate (main, reported) | `cb612b72304246781b7dab48dad77d227c40d45d` | `20f2073aae91a586619e91bbfd33cc93ab9da872` | Reported valid PGP signature; verified at 2026-10-11 22:59:20Z; re-check required | Baseline candidate for new gate evidence; not a release |
| Closure branch HEAD (reported) | `acda4055047b79d3c9e6ee1175c69fafcae49dc0` | `4d3c3758eaa8b8822582f6b5a1a8c2b55ae7ab1f` | Reported unsigned / signature false | Historical closure work only; not canonical |
| Closure predecessor | `7ed133f2caa4844e2d27af8ea2590586546651be` | Not frozen here | Historical Q12 promotion commit | Historical evidence lineage only |
| Old closure identity in docs | `a55a8d36b0a1b61b426c5d59ab44ebd841eb8d53` | `19038af4…` (prefix only) | Stale identity reported | Must not be silently substituted for closure HEAD |
| Historical frozen runtime source | `4cf17cd3befaafeaf64cd4c149739133aa220f73` | `dfe3888bb6adc9aebbb0351efe4a06006f4e0a48` | Historical frozen source; not candidate | Preserve as historical provenance; do not claim candidate coverage |
| Earlier Q10 source in request | `512837c8b1a3e6e8e844252a1b0781d8de011b07` | `43f9cb9691a0d028a1ef396a0a475c5cd80c4a99` | Request marked PREPARED_NOT_EXECUTED | Not evidence of completed scan |

**Freeze rule:** Before accepting any new gate result, capture the live main SHA and tree SHA from GitHub, verify the signature and branch ref, and make the executor state the exact target identity. If the branch head changes, stop and re-freeze; do not re-label old evidence.

## 2. Main vs. closure lineage

Reported comparison:

- Main candidate: `cb612b72304246781b7dab48dad77d227c40d45d`
- Closure HEAD: `acda4055047b79d3c9e6ee1175c69fafcae49dc0`
- Merge base: `b362584a7bf2d3b7e639a0c80292c069ef428344`
- Closure reported 4 commits ahead and 293 behind main.
- The refs have diverged. Do not merge the closure branch wholesale and do not use it as canonical merely because it contains evidence-oriented commits.

At least five identity sets reportedly conflict across handoff documents, main, RELEASE_STATUS, historical frozen source, and Q10/Q12 evidence. Exact per-file analysis is in [Main vs. Closure Comparison](MAIN_CLOSURE_COMPARISON.md).

## 3. Evidence Register

Status labels:
- **REPORTED** — stated in prior evidence summaries; not re-fetched live during drafting.
- **INCOMPLETE** — an attempt or partial output exists, but acceptance conditions are unmet.
- **NOT_BOUND** — no demonstrated binding to the candidate commit/tree.
- **BLOCKED** — a prerequisite or real-world receipt is missing.
- **CANDIDATE** — preliminary evidence only; not a verified gate.
- **NOT_VERIFIED** — verification is not demonstrated.

| Gate / artifact | Reported result | Identity binding | Acceptance status | Required next evidence |
|---|---|---|---|---|
| Q10 Native Codex Security | 2026-10-12 run exit code 2; quota/billing error; preflight 0/649 | Attempt reportedly used source `b96049db9ae206bdc2292108629d8583ea0277d6`, tree `d34446ad0474d644cf09002e35680e7e84ff49d1`; not candidate | INCOMPLETE / NOT_VERIFIED | Full native scan on frozen candidate with valid authorized billing/quota; complete output, exit code, source/tree identity, manifest, timestamps, signature/integrity verification |
| Q11 secure credentialed smoke | Blocked by quota/credit balance; expected `cknexus-q11-smoke.service` absent | Existing evidence tied to historical `4cf17cd3…` source, not candidate | BLOCKED / NOT_VERIFIED | Authorized credential reference in secret manager/systemd credential mechanism, successful live service run, sentinel receipt, sanitized logs, exact source/tree, signed evidence; no secret values in evidence |
| Q12 cgroup v2 | Main artifact claims PASS for `512837c8…` with runner `runner`; closure artifact claims PASS for `cea1d588…` with runner `aibridge` and different cgroup root | Different identities, runner names, roots, and run lineage; neither binds to candidate | CONFLICT / NOT_VERIFIED for candidate | Re-run on approved runner against candidate; prove non-root service identity, delegated cgroup ownership, cpu/memory/pids enforcement, kernel-level observation, run/artifact digest, source/tree and signer |
| Q13 | PASS_CANDIDATE reported | Historical `4cf17cd3…` source | CANDIDATE / NOT_BOUND | Re-run or re-attest by documented policy against frozen candidate; attach complete machine-readable evidence and verification |
| Q14 alert delivery | Older run marked PASS; PR #289 says real alert receipt still required after authorized failure injection | Candidate binding and actual receipt not demonstrated | BLOCKED / NOT_VERIFIED | Authorized failure injection in controlled environment, real downstream alert receipt with provider/message ID and timestamps, end-to-end correlation, safe redaction and signed evidence |
| Q15 | PASS_CANDIDATE reported | Historical `4cf17cd3…` source | CANDIDATE / NOT_BOUND | Candidate-bound execution evidence and independent verification |
| Q16 image/license inventory | Candidate image/license inventory pass reported | Historical source / candidate association not proven | CANDIDATE / NOT_BOUND | Exact image digest, SBOM/license report, source/tree lineage, policy evaluation, artifact digest and independent verification |
| Q05/Q08/Q09 referenced by PR #289 | Q05 626 pass/0 failed, Q08 PASS, Q09 PASS_CANDIDATE reported | PR-head workflows exist, but not equivalent to candidate-wide release evidence | Mixed / NOT_RELEASE_APPROVAL | Validate current exact refs, workflow runs, artifact provenance, required policy criteria and whether each gate requires re-run on frozen candidate |
| SonarCloud | PR checks reported cancelled/failed; project/access lookup 404 reported | Not a successful required check | OPEN / NOT_VERIFIED | Restore correct project binding/permissions and produce a successful check on the exact PR head, or document approved removal/replacement through governance; cancellation is not success |

### Q10 attempt record (do not mislabel as PASS)

Reported:
- Timestamped output directory: `/opt/cknexus/evidence/q10-codex-security/alt-api-20261012T022508Z`
- Exit code: `2`
- Failure: quota/billing error
- Preflight progress: `0/649`
- Result: **incomplete scan; not a security pass**.

Do not copy credentials, API keys, tokens, authorization headers, or secret-bearing environment output into this register or any PR.

## 4. Cross-cutting acceptance criteria

A gate can be marked VERIFIED only if all applicable conditions are met:

1. Exact target commit and tree are frozen and independently checked.
2. Execution is real and attributable to an approved identity.
3. Raw result and relevant logs/artifacts are retained at an access-controlled location.
4. Artifact digest and signature are verified by a separate verifier where required.
5. Result is complete, successful under the gate's actual acceptance policy, and not merely a workflow-level green check.
6. No unresolved identity, timestamp, provenance, permission, or integrity conflict remains.
7. Evidence register and release status are updated with a link to the immutable artifact and verification record.
8. Independent reviewer accepts the evidence; reviewer identity and decision are recorded.

A hash match proves byte identity only; it does not prove execution, correctness, completeness, authorization, or production readiness.

## 5. Required ledger fields for every new artifact

`evidence_id`, gate, artifact URI, created_at_utc, source_commit, source_tree, branch/ref, workflow name, workflow_run_id, runner identity, execution identity, tool/version, command or procedure identifier, exit code, result status, artifact SHA-256, signature/key-id, signature verification result, redaction status, reviewer identity, review decision, supersedes (if any), and notes for limitations.

Never overwrite or mutate a prior artifact. New attempts get new IDs and retain links to failed/superseded attempts.
