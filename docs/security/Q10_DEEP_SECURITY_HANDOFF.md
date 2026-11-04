# Q10 Deep Security Handoff

Q10 is **not passed** by this document or by its CI. This package only prepares an exact, fail-closed handoff for the required native Codex Security Deep Security Scan.

## Frozen target

- Repository: `spinlnw10-art/ck-nexus`
- Commit: `45fde79c717b09f8675645aa541a5834ebd4f433`
- Tree: `8bb93b75237ac9891a6c60854f705459dc263921`
- Scope: `.`
- Mode: `deep`

The scan must operate on that exact target. The preparation branch itself is not the scan subject.

## Required execution contract

The native executor must complete capability preflight, repeated deep discovery, canonical validation, attack-path analysis, canonical draft recording, scan completion, and generated `report.md`. A discovery manifest alone is not final Q10 evidence.

If discovery is capped with zero completed source reviews, coverage must be marked partial and must not be interpreted as no vulnerabilities.

## Evidence required before Q10 can become PASS

1. Exact target commit/tree identity.
2. Native Deep Security terminal discovery manifest.
3. Canonical validation results for all merged candidates.
4. Attack-path decisions for validated/reportable candidates.
5. Canonical scan draft with coverage semantics.
6. Successful scan completion and generated `report.md`.
7. Completion metadata including measured token usage when available.
8. Finding disposition ledger that feeds Q11 validated fixes/regression.

## Fail-closed rules

Bandit, secret scanning, dependency auditing, ordinary CI, or manual review may remain useful supplementary signals, but none can substitute for the native Deep Security executor. Until the completion evidence above exists, Q10 remains `BLOCKED` and Production remains `NO-GO`.

No repository security settings, credentials, production infrastructure, or release gate state are changed by this preparation package.
