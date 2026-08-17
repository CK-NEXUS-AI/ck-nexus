# Security Notes — Gen4 Fusion v0.2

This package is a local design/prototype artifact, not production release evidence.

## Controls implemented

- Fail-closed public claims.
- Append-only immutable evidence objects.
- Evidence freshness handling.
- Subject reconciliation helper.
- Explicit connector lifecycle transitions.
- No ACTIVE connector state without provider-bound evidence and credential reference.
- No write-active connector without explicit approval reference.
- Capability leases are time-bounded and scoped by action/resource.
- High-risk (`R3`/`R4`) execution requires a valid approval object.
- Independent expected-vs-actual effect verification.

## Deliberately not implemented

- Real secret storage or OAuth.
- GitHub/provider mutation.
- Production authentication/RBAC.
- Persistent database/evidence ledger.
- Cryptographic signing of evidence.
- Real sandbox/cgroup enforcement.
- Q10 Codex Security evidence.

A future canonical integration must add those items under the normal CK-NEXUS release gates rather than treating this prototype as proof.
