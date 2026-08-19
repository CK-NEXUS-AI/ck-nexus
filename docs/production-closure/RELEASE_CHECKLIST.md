# CK-NEXUS Final Release Checklist

All checkboxes are evidence requirements, not declarations.

## Frozen authority

- [ ] Runtime source SHA equals `39f5c1adb9d761ab418cf088ff1f051b1ca731d1` unless an approved subject rotation has restarted closure at Q10.
- [ ] Runtime source tree equals `0525195934f703a8becf8a39f6397b2411e0bb2e`.
- [ ] Runtime subject equals `89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52`.
- [ ] PR #14 remains draft/unmerged until final approval.

## Q10

- [ ] Native Codex Security Deep Security Scan completed on exact source/scope.
- [ ] Scan ID recorded.
- [ ] Generated report SHA-256 recorded and independently recomputed.
- [ ] Completion timestamp recorded.
- [ ] Repeated discovery terminal.
- [ ] Canonical validation terminal.
- [ ] Attack-path analysis terminal.
- [ ] Canonical draft accepted.
- [ ] Generated report exists.
- [ ] Coverage acceptable for promotion.
- [ ] No unresolved reportable release-blocking findings.
- [ ] `codex_security_deep_scan=PASS`.
- [ ] `gate_result=PASS`.
- [ ] `production_promotion_allowed=true`.

## Q11

- [ ] Q10 is sealed PASS first.
- [ ] Authorized staging `OPENAI_API_KEY` exists only in GitHub Actions secrets.
- [ ] Exact `verify/q11-final-subject` workflow succeeds.
- [ ] Frozen SHA/tree/subject checks pass.
- [ ] Live Responses API smoke exits 0.
- [ ] `CK-NEXUS-P0-SMOKE-PASS` sentinel observed.
- [ ] No credential value exposed.
- [ ] Artifact ID, server digest, run ID and verifier branch/head recorded.

## Q12

- [ ] Q11 is PASS first.
- [ ] Self-hosted runner carries labels `self-hosted`, `linux`, `cknexus-q12`.
- [ ] Runner UID is non-root.
- [ ] `CKNEXUS_AGNES_CGROUP_ROOT` points to a delegated child boundary, not `/sys/fs/cgroup`.
- [ ] Delegated boundary writable without sudo by runner identity.
- [ ] `cpu`, `memory`, `pids` controllers available.
- [ ] Exact `verify/q12-final-subject` workflow succeeds.
- [ ] `cpu.max`, `memory.max`, `pids.max` observed as expected.
- [ ] Child PID attachment observed.
- [ ] Artifact ID, server digest, run ID and verifier branch/head recorded.

## Provenance

- [ ] All 8 committed release evidence records use the same frozen subject.
- [ ] Artifact IDs resolve and are not expired.
- [ ] Server-side SHA-256 digests match committed evidence.
- [ ] Artifact workflow run IDs match committed evidence.
- [ ] Run repository identity is `spinlnw10-art/ck-nexus`.
- [ ] Verifier branches satisfy the canonical allowlist.
- [ ] PASS/PASS_CANDIDATE evidence originates from successful runs.
- [ ] Q10 PASS contains dedicated native deep-scan provenance.
- [ ] Release evidence provenance result is PASS with zero failures.

## Final Production Package

- [ ] Provenance rechecked before eligibility.
- [ ] All gate conditions pass fail-closed eligibility.
- [ ] Provenance rechecked immediately before packaging.
- [ ] Frozen release tests succeed.
- [ ] Production image builds.
- [ ] Runtime license export succeeds.
- [ ] Production archive created.
- [ ] `SHA256SUMS` created.
- [ ] `sha256sum -c SHA256SUMS` succeeds.
- [ ] `RELEASE_MANIFEST.json` identifies exact commit and runtime subject.
- [ ] GitHub Actions package artifact exists and server-side digest is recorded.

## Release decision

Only after every applicable item above is satisfied may a human reviewer consider marking PR #14 ready, merging, tagging, deployment or a Production Ready claim.
