# CK-NEXUS Seller Checklist — Current Release Closure

**Current decision:** `DEVELOPMENT / RELEASE CANDIDATE — NO-GO FOR PRODUCTION CLAIMS`

**Baseline date:** 2026-11-05 (Asia/Bangkok)

This checklist supersedes the previous checklist bound to runtime subject `96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f`. All earlier PASS and PASS_CANDIDATE records are historical and do not transfer to the current runtime subject.

## Current release identity

- [x] PR #353 merged: canonical runtime entrypoints converge on `creator_app.unified`.
- [x] Current GitHub main SHA: `4d1366cef3cbdd18aa174bdf67308567635c750a`.
- [x] Current Git tree: `57adfe86cd6d9bdbca5c97d336cb733df2308ae5`.
- [x] Current runtime subject manifest SHA-256: `10113cb5874edbaeee2c444e0a8a002f3f68dd7ff6fbd1a72a5b6634a0415227`.
- [x] Frozen closure candidate runtime subject SHA-256: `5129fa855515a13484e9e0e1816eef219f061dd87cc0651eaffae87096741147`.
- [ ] Closure candidate branch and `evidence/RELEASE_SUBJECT.json` frozen.
- [ ] Exact-subject Q10–Q16 artifacts and provenance recorded.
- [ ] Final source package includes Q10–Q16 raw evidence artifacts and provenance manifest; production image archive and SHA256SUMS verified.
- [ ] Production deployment and post-deployment verification completed.

## Technical acceptance gates

- [x] Canonical application runtime and entrypoint unification merged through PR #353.
- [ ] Q10 layered security scans complete: Semgrep, Bandit, Gitleaks, pip-audit, Trivy, security regression, and coverage/completeness.
- [ ] Q10 independent security reviewer attestation and final Owner approval.
- [ ] Q11 live provider test on exact candidate; credential must remain unexposed.
- [ ] Q12 non-root delegated cgroup v2 kernel-enforcement test on the self-hosted runner.
- [ ] Q13 PostgreSQL backup, isolated restore, and sentinel round-trip on exact candidate.
- [ ] Q14 production-rule alert failure-injection and staging receiver delivery on exact candidate.
- [ ] Q15 clean-machine installation on a fresh supported host, including Phase 2 namespace-isolation and Phase 3 autonomous-pipeline regressions.
- [ ] Q16 production image build, immutable image digest, Trivy image scan, and exact runtime license inventory.
- [ ] Final package workflow passes all gate and provenance checks.

## Verified current blockers

- Q10: `NOT_VERIFIED`. The earlier partial run `41912627988` reported one Bandit MEDIUM B310 finding and stale hard-coded issue-state metadata. It is not final evidence. The non-Codex direction is Owner-approved but awaits independent security review.
- Q11: no successful exact-subject live provider run has been verified. The `OPENAI_API_KEY` secret name exists; its value must never be read or exposed.
- Q12: the self-hosted runner was offline. A non-root systemd delegated-cgroup configuration has been prepared but the runner has not yet been started and the kernel gate has not passed.
- Q13–Q16: earlier evidence belongs to older source/tree/runtime subjects and must be rerun.
- Production: no deployment, release tag, or Production Ready claim has been made for this candidate.

## Security and credentials

- [x] Existing production credentials are not included in source or evidence.
- [x] PR #353 does not rewrite Q10–Q16 evidence or deploy production.
- [ ] All new security reports are redacted and their hashes recorded.
- [ ] All medium/high findings have documented disposition.
- [ ] Independent reviewer is a different person from the Owner.
- [ ] Final Q10 approval binds reviewer, Owner, exact candidate SHA/tree, runtime subject, report SHA-256, and workflow run ID.

## Commercial package

- [ ] `THIRD_PARTY_NOTICES.md` and runtime license inventory match the exact production image.
- [ ] Production image archive and source package are included with SHA256SUMS.
- [ ] Installation, configuration, API/runtime, deployment, backup/restore, and rollback guides are current.
- [ ] Transaction-specific legal review completed if required by sale terms.
- [ ] Assignment vs perpetual source license selected in the executed schedule.
- [ ] Seller/buyer legal entities, price, currency, taxes, payment milestones, acceptance period, support, warranty, delivery channel, and backup responsibility defined outside the repository.

## Final decision rule

Mark the package **Production Ready / SELLABLE FOR PRODUCTION** only when Q10–Q16 all report `PASS` against one immutable candidate, the independent security review and final Owner approval are recorded, artifact provenance passes, the production package workflow passes, and post-deployment verification succeeds.

Until then: **NO-GO FOR PRODUCTION CLAIMS.**
