# CK-NEXUS Scanner API hardening

## Scope

This is a proposed, version-controlled replacement for the historical
`/usr/local/libexec/cknexus_scanner_api.py` service. It is not installed or
activated by this change. The live VPS unit and source must remain untouched
until review and an explicit deployment window.

## Security properties

- Binds to `127.0.0.1:8787`; the health endpoint reports service health only.
- Reads the bearer token from a systemd credential file, never from a unit
  environment variable or logs. Authorization comparison uses bytes, so
  malformed/non-ASCII input cannot trigger the old string-comparison exception.
- Restricts scanner names to the fixed `trivy` and `semgrep` allowlist and
  rejects unsupported names rather than silently filtering them.
- Limits request bodies to 1 MiB and requires the exact configured checkout path.
- Requires a clean Git worktree before scanning. Dirty or untracked source fails
  closed with `409 source_not_clean`.
- Records the exact Git commit SHA and tree SHA in every evidence artifact.
- Writes artifacts atomically with mode `0600` and reports the SHA-256 of the
  exact bytes persisted on disk.
- Every result remains `EXECUTED_NOT_VERIFIED`; this service does not set Q10,
  Q11, Q12, Q13-Q16, release, or production gates to PASS.

## Deployment prerequisites — not performed by this PR

1. Review this code and its tests; do not copy it into the live service yet.
2. Create a dedicated `cknexus-scanner` OS account with no interactive login.
3. Grant that account read-only traversal/read access to the selected clean
   checkout and execute access to the approved scanner binaries.
4. Create `/opt/cknexus/evidence/scans` with ownership and permissions that let
   only the dedicated service account write there.
5. Keep `/etc/cknexus-scanner/token` root-owned and mode `0600`; validate that
   systemd credentials are supported by the installed systemd version.
6. Confirm scanner databases/configuration are present and decide whether
   outbound network access is allowed for scanner updates. Do not weaken service
   sandboxing implicitly to make a failed scan pass.
7. Install the unit only during an approved change window, then verify the
   effective unit, process UID, listener address, negative auth tests, and a
   clean-checkout scan. Capture outputs as new, source-bound evidence.

## Known limits

- This API is a local operator endpoint, not a general-purpose job scheduler.
- A clean Git tree is necessary but not sufficient for a trusted release claim.
- Scanner exit codes/findings are recorded as execution results; a successful
  API response is not equivalent to a successful security gate.
- Independent review, Q10 native Codex Security evidence, Q11 live-provider
  execution, Q12 runtime verification, Q13-Q16 closure, and a signed release
  artifact remain separate requirements.
