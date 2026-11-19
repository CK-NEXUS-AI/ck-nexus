# OMNI issuer implementation and deployment gate

Status: issuer core, loopback HTTP transport, and launcher implemented; production deployment NOT YET CONFIGURED.

## Implemented primitives

- `creator_app/council_authority/omni_issuer.py` issues short-lived OMNI contexts only when an explicit `OmniCapabilityRule` matches the skill, granted capability, tool, target, and environment.
- Context proof is Ed25519 over canonical claims containing issuer, agent, execution ID, lease ID, SHA-256 of the complete request/context binding, issue time, and expiry.
- `Ed25519OmniProofVerifier` accepts only a public key and validates the signature and request/context binding. The private key must stay in the issuer process and must never be copied into AGNES.
- `SQLiteOmniIssuerStore` persists lease state and one-use execution binding. Its atomic consume transaction checks binding, lease ID, expiry, revocation, and prior consumption together.
- `creator_app/council_authority/omni_transport.py` provides an authenticated loopback-only HTTP server and AGNES-side client. It caps request bodies, uses short client timeouts, authenticates service tokens, returns no-store responses, and fails closed on unavailable authority calls.
- `scripts/run_omni_issuer.py` loads a protected Ed25519 key, explicit JSON policy, identity-token verification secret, and required evidence-verifier callback from operator-supplied configuration. It refuses non-loopback binds and private keys with group/other permissions.
- Lease TTL is bounded to 1–300 seconds. Production rules are accepted only with E0 risk; approval-required requests need a configured approval verifier. Evidence-required rules fail closed unless an evidence verifier is configured and returns true.

## Mandatory deployment requirements before production

1. Run `scripts/run_omni_issuer.py` as a distinct service/process and security principal from AGNES; do not instantiate `Ed25519OmniIssuer` inside the production AGNES process. Use a dedicated systemd unit and OS account with minimal permissions.
2. Load an Ed25519 private key from a protected secret store or root-readable file. Distribute only the pinned public key to AGNES. No production key is generated or installed by this change.
3. Configure explicit capability rules from reviewed policy; do not derive authorization policy from request fields alone.
4. Provide a trusted evidence verifier and, where required, a trusted approval verifier. The included Council store adapter can be configured with CKNEXUS_OMNI_EVIDENCE_VERIFIER=creator_app.council_authority.omni_evidence:verify, CKNEXUS_COUNCIL_AUTHORITY_DB pointing to the existing evidence database, and CKNEXUS_OMNI_EVIDENCE_KINDS_FILE pointing to an operator-reviewed capability-to-evidence-kind map (example: contracts/omni-evidence-kinds.example.json). Each reference must already exist in the trusted store, be verified/unrevoked, have positive quality, match the request workspace/correlation task binding, and use an allowed kind.
5. Provision a short-lived service token for the configured AGNES service identity; do not add a token-minting endpoint. Pin the issuer public key in AGNES and use HTTPS if transport ever leaves loopback.
6. Exercise the real HTTP boundary, restart/replay, concurrent consume/revoke races, key rotation, expiry, clock skew, and service-unavailable behavior in staging.
7. Wire the AGNES production runtime only after those tests and a configuration gate pass. Until then, the existing production gate must remain fail-closed.

The issuer core tests use ephemeral test keys and temporary SQLite databases only. Passing them is not evidence that a production issuer is deployed or configured.
