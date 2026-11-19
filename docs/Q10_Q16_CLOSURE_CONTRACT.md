# CK-NEXUS Q10-Q16 Production Closure Contract

Adopted for the canonical Q09 baseline `45fde79c717b09f8675645aa541a5834ebd4f433`.

This document maps the remaining production blockers into explicit gates. It is a new closure contract for the current release line; it does not rewrite historical R-series evidence. Every gate is fail-closed. `PASS` applies only to evidence bound to the same immutable release identity. A partial/component pass never promotes the whole gate.

## Q10 — Security and dependency assurance

Required evidence:

- exact-source frozen dependency install: `uv lock --check` and `uv sync --all-extras --dev --frozen`;
- dependency vulnerability audit with no unaccepted finding;
- layered open-source security scans: Bandit static analysis, repository secret scan, frozen-environment pip-audit, and black-box security attack regression;
- successful reports and digests bound to the exact release subject;
- unresolved reportable security finding => FAIL/NO-GO.

No single scanner is sufficient. Q10 remains NOT_VERIFIED until every required scanner and regression succeeds, findings are resolved, and the aggregate evidence is bound to the exact release subject.

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

### Q11 capability sub-gates

The Q11 implementation exposes independently inspectable capability gates:

- Q11-A credential integrity
- Q11-B runtime execution
- Q11-C provider reachability
- Q11-D provider authorization
- Q11-E provider quota
- Q11-F live provider execution
- Q11-G evidence integrity

The aggregate remains fail-closed. The current OpenAI-specific acceptance
condition is not weakened or replaced: a live OpenAI response with the required
sentinel is still required before Q11 can become VERIFIED. A provider error such
as HTTP 429 insufficient_quota is recorded as a provider-specific BLOCKED
condition and cannot be promoted to VERIFIED. Independent gates retain their
own statuses and evidence.
