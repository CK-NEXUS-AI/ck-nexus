# CK-NEXUS Gen4 Fusion Prototype v0.2

A local, non-production implementation of the CK-NEXUS fusion architecture.

## Implemented in v0.2

- Immutable `EvidenceRecord` model and append-only evidence store.
- Evidence freshness and subject reconciliation helpers.
- Strict connector lifecycle with illegal-transition rejection.
- No connector may become active without provider-bound evidence + credential reference.
- `ACTIVE_READWRITE` additionally requires explicit approval reference.
- Capability leases with TTL/action/resource scope.
- Reversibility classes (`R0`–`R4`) and explicit approval requirement for high-risk actions.
- `ExecutionEnvelope` authorization gate.
- Independent effect verifier to detect missing/unexpected side effects.
- Fail-closed Truthful Claims Compiler.
- Read-only FastAPI prototype endpoints for status, evidence, release, and public claims.
- Automated unit/API tests.

## Run locally

```bash
python -m pytest -q
uvicorn backend.app:app --host 127.0.0.1 --port 8765
```

Then open `index.html` or query `http://127.0.0.1:8765/api/claims/public`.

## Safety boundary

This package performs no OAuth, provider calls, GitHub writes, secret retrieval, billing, deployment, or production mutation. It is not Q10/Q11/Q12 evidence and does not modify the frozen production closure subject.
