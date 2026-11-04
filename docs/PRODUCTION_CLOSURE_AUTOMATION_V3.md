# CK-NEXUS Production Closure Automation V3

This document defines the fail-closed handoff from genuine Native Codex Security Q10 evidence through Q11, Q12, provenance reconciliation, and the final checksummed production package candidate.

## Immutable authority

- Runtime source: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Runtime source tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
- Runtime subject: `89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52`
- Production closure PR: #14 remains unmerged until all gates and human review complete.

## Automated chain

1. Native Codex Security produces a genuine sealed scan manifest and `report.md`.
2. `.github/release-tools/codex_security_bridge.py` validates exact SHA, tree, subject, scan ID, completion timestamp, PASS state, and report SHA-256. It cannot create or infer missing Native Scan evidence.
3. `.github/workflows/closure-converge-v3.yml` permits Q11 only after Q10 validation succeeds.
4. Q11 runs `.github/release-tools/q11_live_runner.py` with `OPENAI_API_KEY` supplied only from GitHub Actions secrets. The wrapper rejects missing credentials, missing sentinel, process failure, or detected secret disclosure.
5. Q12 is opt-in and runs only on `[self-hosted, linux, cknexus-q12]`. The runner must be non-root and must receive a writable delegated cgroup v2 root through `CKNEXUS_AGNES_CGROUP_ROOT`.
6. `.github/release-tools/reconcile_provenance.py` re-runs the canonical exact-subject provenance verifier.
7. `.github/release-tools/closure_master.py` refuses convergence unless Q10, Q11, Q12, and provenance all pass on the expected subject.
8. `.github/release-tools/build_final_package.py` builds an exact-source tar archive only after the closure result becomes package-eligible, writes `FINAL_PACKAGE_MANIFEST.json`, and writes `SHA256SUMS`.
9. The generated package remains a release candidate requiring human release review. The automation does not merge PR #14.

## Fail-closed recovery rules

- Missing or malformed evidence: stop.
- Q10 report digest mismatch: stop.
- Q10 target/tree/subject mismatch: stop and rebaseline deliberately.
- Runtime remediation after Q10: rotate subject and invalidate affected subject-bound evidence.
- Missing Q11 secret: remain BLOCKED without logging the secret.
- Q11 sentinel missing or provider call failure: remain BLOCKED/FAIL.
- Q12 root identity, absent delegation, missing controllers, or wrong limits: remain BLOCKED/FAIL.
- Provenance less than the required reconciled set or wrong subject: stop.
- Final package builder never changes production status and never merges a PR.

## Operator invocation after Native Scan

```bash
python .github/release-tools/codex_security_bridge.py \
  --scan-manifest /path/to/sealed/scan-manifest.json \
  --report /path/to/sealed/report.md \
  --output q10-normalized.json
```

The GitHub workflow `CK-NEXUS Closure Converge V3` can then be dispatched with the sealed Q10 artifact paths. Set `run_q12=false` unless the dedicated delegated self-hosted runner is online and correctly configured.

## Status semantics

Preparation success is not Production Ready. Q10/Q11/Q12 production gate state changes only when genuine gate evidence passes and is reconciled against the exact subject. Production remains NO-GO until all required gates, provenance, checksummed final package, and release review complete.
