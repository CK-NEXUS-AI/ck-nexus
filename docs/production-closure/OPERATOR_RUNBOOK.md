# CK-NEXUS Production Closure Operator Runbook

Status: PREPARATION ONLY. This document does not promote any gate.

## Frozen authority

- Repository: `spinlnw10-art/ck-nexus`
- Runtime/source SHA: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Runtime/source tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
- Frozen runtime/deployment subject: `89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52`
- Application subject: `dff89dc7fa9cd6e40480c3344f688a75383ec798929efe23f3a29c79d1186cec`
- Closure PR: #14; remain draft/unmerged until all release gates and packaging pass.

## Mandatory order

`Q10 -> Q11 -> Q12 -> provenance reconciliation -> Final Production Package`

Do not skip a step. If a valid Q10 finding requires a runtime code change, create a new runtime subject, invalidate subject-bound evidence and restart at Q10.

## Q10 native Codex Security Deep Security Scan

The native Codex Security runtime must scan the exact checkout above, target path repository root, scope `.`, mode `deep`. The terminal workflow must include preflight, repeated discovery, canonical validation, attack-path analysis, canonical draft, and completion with generated `report.md`.

Required completion evidence:

- native scan ID
- generated report SHA-256
- completion timestamp
- terminal phase status for every required phase
- coverage state
- zero unresolved reportable release-blocking findings
- `codex_security_deep_scan=PASS`
- `gate_result=PASS`
- `production_promotion_allowed=true`

Do not substitute Bandit, secret scan, pip-audit, ordinary CI or manual review.

After the native scan completes, copy only the exported/sealed metadata and generated report into a temporary operator workspace and run:

```bash
python .github/release-tools/validate_q10_deep_scan.py \
  --metadata /path/to/native-q10-metadata.json \
  --report /path/to/report.md \
  --output q10-deep-scan-validated.json
```

A validator PASS is still not sufficient by itself; the native scan provenance must be committed into the canonical Q10 evidence and reconciled by Release evidence provenance.

## Q11 live provider verification

Use only branch `verify/q11-final-subject` and the existing `verify-q11-final-subject.yml` workflow. The workflow checks out the exact frozen source and verifies its tree and subject before any provider call.

Configure the authorized staging key only as GitHub Actions secret `OPENAI_API_KEY`. Never paste or echo the value into a file, issue, chat, PR, artifact or log. Optional model selection belongs in Actions variable `OPENAI_SMOKE_MODEL`.

PASS requires the live verifier to exit 0 and observe the `CK-NEXUS-P0-SMOKE-PASS` sentinel. Record the resulting run ID, artifact ID, server-side artifact SHA-256 digest, exact verifier branch/head, source SHA/tree, subject and completion time.

Do not trigger the live workflow automatically from preparation tooling because provider execution may incur cost. Execute only after Q10 is sealed PASS and an authorized secret is configured.

## Q12 delegated cgroup v2 verification

Use only branch `verify/q12-final-subject` and its workflow. Required runner labels are `[self-hosted, linux, cknexus-q12]`. The runner identity must be non-root.

Repository Actions variable `CKNEXUS_AGNES_CGROUP_ROOT` must point to a pre-delegated writable cgroup v2 boundary, not `/sys/fs/cgroup`. The delegated boundary must expose `cpu`, `memory`, and `pids` controllers to the runner identity.

The gate `scripts/agnes_cgroup_v2_staging_gate.py` must prove actual values of `cpu.max`, `memory.max`, `pids.max`, and attachment of the child PID. Preparation using sudo is not enforcement evidence; the verification workflow itself must execute as non-root.

## Provenance reconciliation

Only after Q10, Q11 and Q12 are PASS on the same frozen subject, run the existing Release evidence provenance workflow. It must reconcile all eight committed evidence records to server-side GitHub Actions artifact IDs/digests, run IDs, repository identity and allowed verifier branches.

Any subject mismatch, artifact expiry, digest mismatch, run mismatch, wrong repository, wrong branch, or Q10 PASS missing dedicated native deep-scan provenance is a hard failure.

## Final Production Package

Run only after provenance PASS. The existing Final production package workflow performs provenance before eligibility and again before packaging. Production is not ready until the package job succeeds and uploads:

- `CK-NEXUS_PRODUCTION_<commit>.tar.gz`
- `SHA256SUMS`
- `RELEASE_MANIFEST.json`

Verify `sha256sum -c SHA256SUMS` before any Production Ready claim.

## Current stop condition

Until a native Q10 scan is completed and sealed, status remains `NO-GO`. Q11/Q12 may be prepared but must not be promoted from preparation alone.
