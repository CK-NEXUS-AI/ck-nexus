# CK-NEXUS Q10–Q16 Production Closure Runbook

**Current baseline date:** 2026-11-05 (Asia/Bangkok)

**Decision:** `NO-GO FOR PRODUCTION CLAIMS` until all seven gates and approvals pass.

## 1. Current immutable runtime baseline

| Identity | Value |
|---|---|
| GitHub main source | `34d7df48b35903d7861362a72b0d3a1fd8a3b201` |
| Git tree | `af57e2a5202bc95bb07d321c65a57a623205333b` |
| Runtime subject manifest SHA-256 | `3f414a4329d35f57cbc05b49f11cb34a184b276dbe1b528792d8cb4317dcc2f6` |
| Canonical runtime | `creator_app.unified` |
| Runtime-unification PR | #353 — MERGED |

These values identify the main baseline before the closure remediation branch. The closure branch may change documentation, workflows, scripts, and tests, but it must not change runtime-subject paths without creating a new subject and rerunning every affected gate. All gates must be run against one final release candidate SHA/tree/subject, not a moving `main` reference.

The VPS production source and active service unit are older than this baseline. No deployment or production restart has been performed. Do not update the production source or service until release eligibility is established.

## 2. Q10 — Open-source layered security

The Owner approved the non-Codex evidence direction on 2026-11-05. This is not an equivalence claim. The decision record is `docs/evidence/Q10_NATIVE_SCAN_RETIREMENT_DECISION.md`; independent security review remains mandatory.

The canonical Q10 workflow is `.github/workflows/q10-evidence-gate.yml`. It must scan the exact release candidate and preserve:

1. Semgrep static analysis with pinned tool version/ruleset.
2. Bandit Python security analysis.
3. Gitleaks repository-history and tracked-file scan with secret redaction.
4. `pip-audit` against the frozen dependency environment.
5. Trivy filesystem and configuration scan.
6. CK-NEXUS security attack regression suite.
7. Coverage/completeness evidence, tool versions, exit codes, raw report hashes, exact source SHA/tree, and runtime subject.

A successful workflow means scanner execution completed; it does **not** mean the whole Q10 gate is approved. The immutable automated report remains `READY_FOR_HUMAN_REVIEW` with `gate_result=NOT_VERIFIED` and `production_promotion_allowed=false`. The provenance verifier checks a real APPROVED PR review by a different repository collaborator and a later comment from the pinned repository Owner account (`spinlnw10-art`), both containing the exact candidate SHA and report SHA. The final release manifest may record an effective Q10 `PASS` only after those API-backed attestations are verified; the scanner evidence itself is never rewritten.

Blocking conditions include exposed credentials, dependency vulnerabilities, critical/high issues, medium/high Bandit findings, Semgrep ERROR findings, failed security regression, missing reports, and incomplete scanner execution. Medium findings require a documented reviewer disposition. Low/informational findings remain visible.

The preliminary main-branch run `41912627988` is not final evidence: it used the earlier partial workflow, reported a Bandit MEDIUM B310 finding, and contained stale hard-coded issue-state metadata. Do not promote it.

## 3. Q11 — Live provider integration

Run `scripts/test_openai_live.py` against the exact release candidate using the GitHub Actions secret `OPENAI_API_KEY`. The secret name exists in repository settings; its value must never be read, printed, or placed in evidence.

PASS requires an actual live Responses API request, expected sentinel `CK-NEXUS-P0-SMOKE-PASS`, `credential_configured=true`, `credential_exposed=false`, and an evidence artifact bound to the final source SHA/tree/runtime subject. A mock or offline test is not Q11 evidence. The Q11 workflow is candidate-aware and accepts an exact source SHA; collection rejects any run whose evidence SHA does not equal the workflow run head SHA.

## 4. Q12 — Delegated cgroup v2

Q12 requires actual kernel-enforced CPU, memory, and PID limits under a non-root service identity. Merely detecting cgroup v2 is insufficient.

The registered `cknexus-q12` self-hosted runner was activated temporarily for this closure run; its systemd unit remains disabled at boot and must be stopped after Q12 evidence collection. A systemd drop-in has been prepared at `/etc/systemd/system/actions.runner.spinlnw10-art-ck-nexus.cknexus-q12.service.d/10-nonroot-delegated-cgroup.conf`: it runs `/opt/actions-runner/runsvc.sh` as the dedicated non-root `runner` identity with `Delegate=cpu memory pids` and `DelegateSubgroup=supervisor`. Repository variable `CKNEXUS_AGNES_CGROUP_ROOT` points to the service cgroup parent `/sys/fs/cgroup/system.slice/actions.runner.spinlnw10-art-ck-nexus.cknexus-q12.service`. The service is currently active only for this closure session; it remains disabled at boot and must be stopped after the Q12 run. The Q12 workflow verifies the runner is in the `supervisor` subgroup, enables only `cpu`, `memory`, and `pids` in the delegated parent, and requires its `cgroup.procs` to remain empty. Never make `/sys/fs/cgroup` globally writable or use `chmod 777`.

PASS requires observed `cpu.max=20000 100000`, `memory.max=67108864`, `pids.max=16`, successful child-process attachment, and evidence bound to the final candidate. The runner may be started temporarily for Q12 and stopped after the run; do not enable it at boot without a separate operational need.

## 5. Q13 — PostgreSQL disaster recovery

Run `scripts/gate_postgres_dr.py` against an isolated staging restore target. Capture backup integrity, restore completion, sentinel round-trip, PostgreSQL tool versions, and artifact hashes. Never use the current seller working database as a destructive target.

## 6. Q14 — Observability and operator alert delivery

Use the production alert rules with controlled failure injection and an isolated staging webhook receiver. Verify the required `CKNexusEmailStaleLeases` alert reaches the receiver after its configured `for` duration, and separately verify CK-NEXUS health/metrics. Preserve the alert receipt hash, Prometheus/Alertmanager image identities, runtime logs, and exact-subject metadata. A static rule-file check is not sufficient.

## 7. Q15 — Clean-machine deployment

Install the exact candidate artifact on a genuinely fresh supported machine or isolated VM. Capture machine identity/class, install commands, dependency resolution, start logs, health checks, functional smoke tests, and elapsed time. Re-running on the existing VPS or Termux device is not clean-machine evidence.

## 8. Q16 — Production image, license inventory, and release convergence

Build the image from the exact candidate, record its immutable digest, scan the image and runtime dependencies, and generate the third-party license inventory/notices from the built image. Verify the clean source package and its SHA-256 from an independent location. Q16 cannot pass while any Q10–Q15 gate, independent review, Owner approval, or release provenance check remains unresolved.

## 9. Evidence and release invariants

- Every Q10–Q16 evidence file must reference the same final runtime subject and exact candidate source SHA/tree.
- Every artifact must include the successful workflow run ID, artifact ID, server-side artifact digest, raw report SHA-256, and completion timestamp.
- A historical PASS or PASS_CANDIDATE from another source SHA/tree/subject is not transferable.
- No evidence is rewritten to manufacture PASS. New runs create new evidence; historical files are preserved in Git history.
- `NO EVIDENCE → NO DONE`. The release is production-eligible only after all gates, independent review, Owner approval, provenance verification, and post-deployment verification pass.
