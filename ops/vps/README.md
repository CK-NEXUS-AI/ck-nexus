# CK-NEXUS VPS Operations Archive

This directory is a source-control archive of helper scripts found in `/root` on the VPS during the migration audit on 2026-10-23.

## Safety

- These are archived for review and recovery; do not run an unfamiliar script blindly.
- Scripts with cleanup, reclaim, reboot, key installation, account login, or service-management behavior may be destructive or environment-specific.
- Review each script and replace machine-specific paths/addresses before reuse.
- No runtime `.env` files, API keys, OAuth tokens, private keys, database files, user uploads, or credential JSON files belong in GitHub.
- `cknexus-install-q11-key.sh` was deliberately excluded pending credential-flow review. JSON files such as `cknexus-key-list.json`, `cknexus-old-key-disable.json`, and `.claude.json` were not copied because their names/content may contain credential or account state.

## Inventory scope

`./scripts/` contains shell and Python helper scripts found at `/root/*.sh` and `/root/*.py`, except the excluded key-installation script. This is not yet a full VPS image: systemd units, service configs, Docker volumes, databases, and runtime state require separate review and sanitized export.
