# CK-NEXUS Production Closure Master V2

Status: **PREPARED / PRODUCTION NO-GO**

This document is operational preparation only. It cannot promote Q10, Q11, Q12, provenance, or the final package without genuine machine evidence.

## Exact authorities

- Repository: `spinlnw10-art/ck-nexus`
- Closure PR: `#14` (Draft/Open/Unmerged)
- Closure head: `a55a8d36b0a1b61b426c5d59ab44ebd841eb8d53`
- Runtime/security source and Q10 target: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Runtime/security tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
- Frozen runtime/deployment subject: `89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52`
- Unified application subject: `dff89dc7fa9cd6e40480c3344f688a75383ec798929efe23f3a29c79d1186cec`

Authority order: Live GitHub → Closure Evidence → Release Artifacts → Historical Chat.

## CK-NEXUS DNA

`USER → ACCESS → CK-NEXUS COGNITIVE GOVERNOR → TASK GRAPH → AGNES/AGENTS → MODEL/TOOL → SANDBOX → VERIFICATION → EVIDENCE VAULT → RESULT`

Required invariants: authority separation; evidence-first execution; exact-subject verification; credential isolation; capability-based access; fail-closed governance; provider independence; agent specialization/council; UI/runtime truthfulness.

## Q10 native Codex Security Deep Security Scan

Use the exact checkout of runtime/security source, not moving `main` and not a development PR:

```bash
git fetch --all --tags --prune
git checkout --detach 39f5c1adb9d761ab418cf088ff1f051b1ca731d1
test "$(git rev-parse HEAD)" = "39f5c1adb9d761ab418cf088ff1f051b1ca731d1"
test "$(git show -s --format=%T HEAD)" = "0525195934f703a8becf8a39f6397b2411e0bb2e"
```

Open that exact checkout in a host with the native Codex Security plugin server and run the Deep Security Scan with `targetPath=<exact checkout>` and `scope="."`. The native deep-scan coordinator owns repeated independent Standard scans, validation/attack-path reasoning inside those scans, aggregation, canonical parent artifacts, and then exactly one `complete_codex_security_scan` seals the report.

Required capture after successful completion:

- `codex_security_scan_id`
- SHA-256 of sealed `report.md`
- completion timestamp
- exact target SHA
- exact target tree SHA
- exact frozen runtime subject

`Bandit`, `pip-audit`, secret scan, ordinary CI, manual review, or GPT-vs-GPT simulation are supplementary only and are forbidden substitutes.

### Q10 remediation / subject rotation

If a validated finding requires a change to any frozen runtime path:

1. Stop promotion immediately.
2. Patch on a new candidate branch.
3. Compute the new runtime source/tree/subject.
4. Mark all old subject-bound Q10/Q11/Q12/provenance evidence `SUPERSEDED`.
5. Rebind verifier branches/workflows to the new exact source/subject.
6. Restart at Q10. Never transplant the previous PASS fields.

## Q11 live provider verification

Use `verify/q11-final-subject` and existing live smoke implementation. Credential policy:

- provider secret exists only in an authorized secret store (for GitHub Actions, repository/environment secret `OPENAI_API_KEY`);
- never commit, print, archive, paste, or include the raw key in evidence;
- agent/model receives only the minimum brokered/runner-provided capability needed for the smoke;
- evidence must state `credential_exposed=false`.

PASS must come from the live workflow and include live sentinel success, exact release subject, workflow run ID, artifact ID, and server-side artifact digest. `evidence/q11/Q11_LIVE_PROVIDER_TEMPLATE_V2.json` remains BLOCKED until replaced from genuine machine evidence.

## Q12 delegated cgroup v2

Use a dedicated staging/self-hosted Linux runner executing as a non-root CK-NEXUS service identity. The service manager must delegate `cpu`, `memory`, and `pids` controllers to a writable subtree. Do not use root/sudo or globally relax `/sys/fs/cgroup` to manufacture evidence.

Required observations:

- non-root identity;
- writable delegated boundary;
- `cpu.max = 20000 100000`;
- `memory.max = 67108864`;
- `pids.max = 16`;
- child process attached to the intended cgroup;
- CPU, memory, and PID limit tests succeed;
- escape attempt is blocked;
- workflow run ID, artifact ID/digest, and exact runtime subject recorded.

Use `verify/q12-final-subject`; adapt only the runner/execution environment required for genuine non-root delegation. If verifier logic or a frozen runtime path changes, apply the subject-rotation rule.

## Provenance reconciliation

After Q10, Q11, and Q12 are genuinely PASS, rerun the repository's canonical provenance verifier against:

`89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52`

Acceptance requires at least the currently expected 8/8 records, zero provenance failures, exact repository/run/artifact/digest/subject bindings, and freshness after the final prerequisite gate. Historical 8/8 results are candidate history only until rerun after the three blockers close.

## Final package

Only after Q10/Q11/Q12/provenance PASS may the Final Production Package workflow run. The package must be content-addressed/checksummed and its digest recorded. Packaging success makes the subject eligible for human release review; it does not authorize an automatic merge of PR #14.

## Automated fail-closed integrity check

```bash
python .github/release-tools/closure_master.py \
  --q10 /path/to/Q10.json \
  --q10-report /path/to/report.md \
  --q11 /path/to/Q11.json \
  --q12 /path/to/Q12.json \
  --provenance /path/to/release-evidence-provenance.json \
  --package /path/to/final-production-package.zip \
  --output closure-final-verification.json
```

Missing or mismatched evidence returns non-zero and retains NO-GO.

## GPT-parallel simulation semantics

GPT-vs-GPT tests are architecture/contract tests only. Roles are Governor, Intelligence Provider, Independent Verifier, and Scenario Generator. They may validate authority separation, evidence requirements, fail-closed behavior, provider independence, council semantics, failure/recovery decisions, and UI truthfulness. They can never satisfy Q10 native security evidence, Q11 real-provider evidence, Q12 host isolation evidence, or final production evidence.

## Release claim matrix

- `VERIFIED`: backed by exact, current machine evidence.
- `PASS_CANDIDATE`: evidence exists but final prerequisite/reconciliation is incomplete.
- `DESIGN_ONLY`: architecture/spec/test design only.
- `MISSING/BLOCKED`: mandatory evidence or environment absent.

Current production classification remains **NO-GO** until every mandatory gate and the checksummed final package complete.
