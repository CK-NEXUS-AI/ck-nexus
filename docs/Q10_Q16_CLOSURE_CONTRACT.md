# CK-NEXUS Q10-Q16 Production Closure Contract

Historical baseline: canonical Q09 `45fde79c717b09f8675645aa541a5834ebd4f433`.

Current re-baseline (2026-11-05): source `34d7df48b35903d7861362a72b0d3a1fd8a3b201`, tree `af57e2a5202bc95bb07d321c65a57a623205333b`, runtime subject `3f414a4329d35f57cbc05b49f11cb34a184b276dbe1b528792d8cb4317dcc2f6`. The old Q09 baseline and all earlier Q10–Q16 evidence are historical and are not transferable to this subject.

This document maps the remaining production blockers into explicit gates. It is a new closure contract for the current release line; it does not rewrite historical R-series evidence. Every gate is fail-closed. `PASS` applies only to evidence bound to the same immutable release identity. A partial/component pass never promotes the whole gate.

## Q10 — Security and dependency assurance

Required evidence:

- exact-source frozen dependency install: `uv lock --check` and `uv sync --all-extras --dev --frozen`;
- Semgrep static analysis, Bandit Python analysis, Gitleaks repository/history scan, frozen-environment `pip-audit`, and Trivy filesystem/configuration scan;
- CK-NEXUS security attack regression and coverage/completeness verification;
- tool versions, rule/configuration versions, per-tool exit codes, raw report hashes, source SHA/tree, runtime subject, and successful workflow provenance;
- no exposed credential, dependency vulnerability, critical/high issue, medium/high Bandit issue, Semgrep ERROR, or failed security regression;
- documented independent review of all findings, non-equivalence, scanner coverage and false-positive handling.

The Owner approved the non-Codex evidence direction on 2026-11-05; see `docs/evidence/Q10_NATIVE_SCAN_RETIREMENT_DECISION.md`. This is not an equivalence claim. The immutable scanner evidence remains `NOT_VERIFIED` and is never rewritten. The release provenance verifier independently validates a real APPROVED GitHub PR review and a later Owner approval comment, both bound to the candidate SHA and report SHA. Only then may the final release manifest record an effective Q10 `PASS`.

## Q11 — Live AI/provider gate (P0-AI-001)

Run `scripts/test_openai_live.py` against the exact release identity with seller/buyer-authorized project-scoped staging credentials. PASS requires a live Responses API request and the expected `CK-NEXUS-P0-SMOKE-PASS` sentinel. Missing credentials, SDK failure, account/model denial, or missing sentinel => BLOCKED/FAIL.

## Q12 — Delegated cgroup v2 staging enforcement

Run `scripts/agnes_cgroup_v2_staging_gate.py` on staging Linux with delegated cgroup v2 available. PASS requires observed CPU, memory and PID limits plus successful child-process attachment. Hosted/local simulation without delegated cgroup control is not sufficient.

## Q13 — PostgreSQL disaster-recovery backup/restore

Run `scripts/gate_postgres_dr.py` against an authorized staging source and isolated destructive restore target. PASS requires backup and restore completion with PostgreSQL client tools available and explicit isolated-staging approval. Never use the current seller working database as a destructive target.

## Q14 — Observability and operator-alert delivery

Static alert-rule presence alone is insufficient. Run failure injection on staging, capture operator alert delivery evidence, set `CKNEXUS_ALERT_RECEIPT_FILE`, and run `scripts/gate_observability.py` / `scripts/p0_observability_check.py`. PASS requires healthy runtime/metrics and captured operator-alert evidence for the required alert path.

## Q15 — Clean-machine deployment

Install the exact release artifact on a fresh supported VM/host. Record host identity/class, install commands, dependency resolution, start logs, health/smoke results and elapsed duration. Same-host reruns are not clean-machine evidence. `scripts/gate_clean_machine.py` intentionally remains fail-closed until deployment-specific evidence is collected.

## Q16 — Final release convergence and commercial delivery

Only after Q10-Q15 PASS:

- integrate approved Unified Control changes into the exact release branch;
- rerun full frozen CI/security/regression on the final combined tree;
- run strict commercial release checks;
- remove unresolved repository commercial placeholders;
- generate/review exact dependency-license/third-party notices;
- refresh `RELEASE_STATUS.md`, seller checklist and delivery manifest;
- build a clean source artifact, verify internal/external SHA-256 values;
- merge through reviewed GitHub PR and create the final immutable release tag/artifact.

Q16 is PASS only when all prior gates and final-tree checks are PASS. Until then the decision remains **NO-GO FOR PRODUCTION CLAIMS**.
