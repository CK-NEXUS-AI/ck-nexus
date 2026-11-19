# CK-NEXUS R8 — Persistent Encrypted Credential Vault

Baseline: R7 commit `11b35ca94937b98264e996e9e22c5dea20d9ffb6`.

Release posture remains **Development Candidate / Release Candidate / NO-GO**.

## Implemented in this slice

- Persistent SQLite credential vault with Fernet authenticated encryption.
- Vault master key remains outside the database and is supplied through
  `CKNEXUS_VAULT_KEY`; the vault file is forced to owner-only mode on supported
  filesystems.
- Credential Broker resolution order is now ephemeral runtime value, encrypted
  persistent value, then environment compatibility value.
- Persistent credential creation/rotation, local revocation, expiry handling,
  redacted audit events, and transactional master-key rewrap.
- Gmail refresh tokens use the encrypted vault when configured; access tokens
  remain short-lived runtime values. Local token revocation clears both layers.
- GitHub App installation tokens can persist encrypted with their TTL so a process
  restart does not require an unnecessary token mint while the token remains valid.
- Safe vault status/audit API surfaces expose metadata only and never ciphertext,
  plaintext credentials, or the encryption key.
- Production startup remains fail-closed and now additionally requires an enabled
  vault plus configured vault key when Gmail OAuth or GitHub App auth is enabled.

## Validation in this environment

- Vault/config/OAuth/GitHub targeted tests: 25 PASS.
- Final non-billing regression after vault integration: 95 PASS.
- Python compile: PASS.
- TOML parse: PASS.
- Worktree secret-pattern scan: PASS.
- Full billing suite: BLOCKED in the available test environment because SQLAlchemy
  is not installed at collection time.

## Still blocked / not production evidence

- AI001 live OpenAI execution is not claimed; no authorized runtime OpenAI key was
  used in this slice.
- Live Gmail OAuth refresh/revocation against Google is not yet evidenced.
- Live GitHub App installation-token mint/revoke is not yet evidenced.
- PostgreSQL, deployed n8n, backup/restore, alert delivery, and clean-machine gates
  remain inherited P0 blockers.
- Key custody for production should move from a plain environment variable to an
  OS/cloud secret manager or workload identity path where available.
