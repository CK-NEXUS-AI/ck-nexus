# R24 Council Capability Authority Hardening

R24 hardens the collaborative Council runtime without replacing the existing CK-NEXUS Credential Broker/Vault.

## Security invariants

1. Caller identity is derived from a signed service token; request bodies cannot choose their own agent identity.
2. Registered capabilities are fail-closed and agent permissions are evaluated only by the Python authority.
3. Source-sensitive capabilities require a verified Evidence Registry entry; arbitrary evidence strings do not satisfy the gate.
4. Every approved execution is bound to canonical parameters by SHA-256 and receives a short-lived, signed, one-time grant.
5. Sensitive handlers must consume the grant before execution. The SDK is not itself the security boundary.
6. Credential authorization reuses `creator_app.credential_broker.CredentialBroker`; plaintext credentials never enter policy decisions.
7. Cost reservations use SQLite transactions. Administrative top-up is itself an admin-only capability.
8. Safety veto requires both policy authorization and verified evidence. A veto blocks the risky decision rather than selecting the vetoing proposal as the winner.
9. Close arbitration scores fail to `BLOCKED_HUMAN_REVIEW` rather than guessing.
10. Audit records are hash chained and contain identifiers/hashes, not credential values.

## GitHub source verification

Council engineering may not claim source verification until GitHub repository access resolves and a verified git-commit evidence reference is present. With zero accessible repositories/installations, the authority fails closed.
