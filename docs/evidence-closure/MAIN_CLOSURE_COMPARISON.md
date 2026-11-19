# Main vs. Closure Comparison

**Purpose:** Preserve divergence and identity conflicts without promoting either historical closure evidence or stale documentation into current truth.

## 1. Reference table

| Field | Main candidate (reported) | Closure branch (reported) |
|---|---|---|
| Ref | `main` | `release/q10-q16-closure` |
| Commit | `cb612b72304246781b7dab48dad77d227c40d45d` | `acda4055047b79d3c9e6ee1175c69fafcae49dc0` |
| Tree | `20f2073aae91a586619e91bbfd33cc93ab9da872` | `4d3c3758eaa8b8822582f6b5a1a8c2b55ae7ab1f` |
| Signature | Reported valid PGP signature | Reported unsigned / signature false |
| Relation | Candidate baseline | Diverged historical evidence branch |
| Merge base | `b362584a7bf2d3b7e639a0c80292c069ef428344` | Same |
| Relative count | Reported 293 commits ahead of closure | Reported 4 commits ahead of main |

These counts and identities are reported from the preceding audit summary and must be rechecked against the live GitHub refs before a release decision. This document itself does not run a new Git comparison.

## 2. Stale and conflicting identity references

- Main `RELEASE_STATUS.md` reportedly references old main identity `45fde79c…` and closure identity `a55a8d36…`, not the candidate and current closure HEAD listed above.
- Closure `RELEASE_STATUS.md` is also reported stale.
- The Q10 request file reports `PREPARED_NOT_EXECUTED` and targets `512837c8…` / tree `43f9cb96…`; it separately lists frozen runtime source `4cf17cd3…` / tree `dfe3888b…`.
- Historical Q11/Q13/Q14/Q15/Q16 artifacts are reported to reuse the `4cf17cd3…` source identity and are not proven to cover the current candidate.
- The main and closure Q12 artifacts are materially different despite sharing the same filename and manifest prefix.

## 3. Q12 artifact collision / non-equivalence

| Field | Main artifact (reported) | Closure artifact (reported) |
|---|---|---|
| Source commit | `512837c8…` | `cea1d5880eb8aee4a23d26dbf2d6443748270254` |
| Runner user | `runner` | `aibridge` |
| cgroup root | `/sys/fs/cgroup/cknexus-delegated` | `/sys/fs/cgroup/system.slice/actions.runner.spinlnw10-art-ck-nexus.cknexus-q12-vps.service/work` |
| Claimed status | PASS | PASS |
| Artifact lineage | Different source and runtime context | Reported GitHub artifact ID `10577158236`, run `35421281024` |
| Integrity note | Not candidate-bound | Reported digest `sha256:7afd6dbcdafbdf4557346ca1e604be114b0c374031d23dd159c62ca60307cf62`; manifest prefix `96dcd0f…` |

Both records must be retained as distinct historical artifacts. Neither proves Q12 for `cb612b72304246781b7dab48dad77d227c40d45d`. The closure artifact's reported `production_promotion_allowed: true` field conflicts with the open gate blockers and is not an authorization signal. Policy and gate evidence take precedence over a free-form artifact flag.

## 4. Safe reconciliation procedure

1. Read the live `main` and closure refs; record UTC time, full SHA, tree SHA, signature status, and API/browser source.
2. Freeze the candidate identity in a new immutable audit record. Do not alter historical evidence to match it.
3. Inspect each evidence artifact's embedded source commit/tree and manifest. Classify as candidate-bound, historical, conflicting, incomplete, or unverifiable.
4. Keep the closure branch isolated. Do not merge it wholesale into main; it is reported as heavily diverged.
5. Fix stale status documentation only in a separately reviewed docs PR after the current facts are revalidated. Do not use the closure branch's old release status as source of truth.
6. Re-run missing gates against the frozen candidate where technically and policy-appropriate.
7. Have an independent reviewer verify identity and evidence lineage before changing any gate state.
8. Re-freeze if main advances. Evidence for a prior candidate remains evidence for that prior candidate; it does not automatically transfer to a newer commit.

## 5. Decision

**No canonical release artifact has been established by this comparison.** Main candidate identity is a working baseline only. Closure branch is historical, divergent, and reported unsigned. Production remains NO-GO until gate evidence is complete, candidate-bound, verified, and independently accepted.
