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

## Q11 — Live AI/provider gate (P0-AI-001) — v2 (2026-11-11 amendment)

Run `scripts/test_openai_live.py` against the exact frozen release identity with seller/buyer-authorized staging credentials. PASS requires a successful live provider API request and the expected `CK-NEXUS-P0-SMOKE-PASS` sentinel observed in the real provider response. Evidence must record the actual provider, model, base URL where applicable, response/run identity, and `credential_exposed: false`.

OpenAI Responses API remains the preferred/reference provider. OpenAI-compatible providers using `/chat/completions` (including Groq, OpenRouter, and Cerebras where supported) are accepted under this explicitly disclosed amendment when the provider, base URL, and model are recorded and the live sentinel is observed. For a non-OpenAI provider, evidence must include `contract_amendment: "v2-allows-openai-compatible"` and amendment date `2026-11-11`.

Missing credentials, unavailable SDK/runtime, API denial, network failure, mocked responses, or missing sentinel => BLOCKED/FAIL. A provider smoke PASS closes only Q11 for the exact evidence subject; it does not imply Q10 or overall production promotion.

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

### Q11 Current Status (2026-11-11)

**AMENDED but PENDING BUYER VERIFICATION.** The v2 contract accepts OpenAI-compatible providers, and `scripts/test_openai_live.py` implements OpenAI Responses plus Groq/OpenRouter chat-completions paths. The Termux Android ARM64 implementation and wrapper are prepared; the silent key loader is maintained outside the repository.

The current environment's live attempts are **BLOCKED**, not PASS: Groq returned HTTP 403 from the current network; the selected OpenRouter free model returned HTTP 404 (retired/unavailable), and the alternative returned HTTP 402 (credit/quota required); OpenAI has no available credit. No sentinel was observed. No further free-provider retries are planned for this closeout.

Resolution: the buyer performs Q11 verification with their own funded OpenAI API account (the proposed initial credit is approximately USD 5, subject to actual provider pricing) or reruns the accepted compatible-provider test from a network/provider account where access is available. Buyer execution must produce fresh evidence bound to the buyer's exact release subject. Q11 remains unverified until that evidence records a successful live response and the expected sentinel.

Evidence: `evidence/Q11_OPENAI_LIVE.json` records the current pending buyer-verification state and observed blockers. `scripts/run_q11_groq.sh` invokes the Groq test wrapper; the silent credential loader is stored outside the repository. This pending state does not grant Q11 PASS or production promotion.
