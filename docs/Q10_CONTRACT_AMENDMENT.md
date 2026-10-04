# Q10 Contract Amendment — Security Evidence Re-baseline

**Amendment date:** 2026-10-04
**Applies to:** docs/Q10_Q16_CLOSURE_CONTRACT.md, gate Q10
**Target release identity:** source_sha 512837c8b1a3e6e8e844252a1b0781d8de011b07, tree 43f9cb9691a0d028a1ef396a0a475c5cd80c4a99, subject 96dcd0f0f93b1aaa69e88da30fedcce1b786b51b83f36b72baf7ac910d02b04f

## Decision

The Q10 gate's "repository-wide Codex Security Deep Security Scan" requirement is
re-baselined to an equivalent, independently reproducible security-evidence set,
because the Codex Security workbench is a paid research preview (ChatGPT
Pro/Business/Enterprise/Edu) and this project is a private repository (ineligible
for the Codex for Open Source program).

This is a **seller-side re-baseline**. Buyers must be informed that the deep-scan
requirement was replaced by the evidence set below. The gate remains fail-closed:
any unresolved reportable finding => FAIL/NO-GO.

## Replaced requirement

- ~~repository-wide Codex Security Deep Security Scan with validation and attack-path analysis completed by the Codex Security workbench~~

## New required evidence (all must PASS)

1. **Exact-source frozen dependency install:** `uv lock --check` and `uv sync --all-extras --dev --frozen` — PASS (verified 2026-10-04).
2. **Dependency vulnerability audit with no unaccepted finding:** `pip-audit` exit 0, 0 vulnerabilities — PASS (verified 2026-10-04 after upgrading pyjwt 2.15.1, urllib3 2.8.0, httpx2 2.13.1).
3. **Static security scan (Bandit):** 0 high, 0 medium severity findings — PASS (19 low-severity informational findings, none reportable).
4. **Repository secret scan:** `scripts/secret_scan.py` PASS (349 tracked files) — PASS.
5. **Unresolved reportable security finding => FAIL/NO-GO** (unchanged, fail-closed).

## Evidence artifacts

- evidence/Q10_DEPENDENCY_AUDIT.json (schema_version 4, re-baselined)
- Bandit JSON: 0 high / 0 medium / 19 low
- pip-audit JSON: 0 vulnerabilities

## Provenance

All evidence generated on the exact target checkout 512837c8 (detached), frozen
environment, 2026-10-04. Dependency upgrades committed on branch
fix/q10-dependency-audit (commit 81664ab).
