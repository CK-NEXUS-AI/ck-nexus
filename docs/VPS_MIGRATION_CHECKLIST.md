# VPS to GitHub Migration Checklist

Audit date: 2026-10-23
Repository: `CK-NEXUS-AI/ck-nexus`

## Completed and pushed

- [x] Existing local CK-NEXUS commits and current repository changes pushed to `main`.
- [x] Tool discovery and n8n workflow dashboard source/tests added.
- [x] Root-level helper shell/Python scripts archived in `ops/vps/scripts/` (excluding `cknexus-install-q11-key.sh`, which needs credential-flow review).
- [x] Selected installed CK-NEXUS service source files archived in `ops/vps/services/`.
- [x] Selected CK-NEXUS systemd unit and timer files archived in `ops/vps/systemd/`.
- [x] Python compilation, shell syntax, Node syntax, and targeted test suite checked. Targeted pytest result: 58 passed.
- [x] Secret-pattern scans on newly archived service/script files returned no matches for the checked token/private-key patterns. This is not a guarantee that every possible secret is absent.

## Explicitly excluded

- Runtime `.env` files and credential/account-state JSON files (including `.claude.json`, `cknexus-key-list.json`, and `cknexus-old-key-disable.json`).
- API keys, OAuth tokens, private keys, database contents, Nextcloud user files, n8n credentials, and live application data.
- Backup copies of scripts and service files.

## Not yet migrated / not safe to delete VPS

- Docker named volumes and container writable layers, including Nextcloud/MariaDB/Redis, TryPost/Postgres/Redis, Keycloak, SearXNG, CK-NEXUS containers, and Docker Assistant.
- n8n runtime database, workflow credentials, encryption key, binary data, and application configuration.
- Nextcloud data directory, database, Caddy configuration/certificates, and user files.
- Actual environment files and credential stores required to recreate services. These should be backed up encrypted or stored in an approved secret manager, never committed to Git.
- Other service files/configs outside the selected unit list; system users/groups, firewall rules, Tailscale identity, cron jobs, mounted disks, and any external DNS/tunnel setup.
- Full restore test on a clean host.

## Required before VPS reset

1. Inventory every Docker volume, bind mount, database, and service-specific data path.
2. Create encrypted backups of required runtime data and secrets; verify archive integrity.
3. Confirm all GitHub commits are present and repository working tree is clean.
4. Prepare a clean-host deployment procedure using sanitized templates and secret injection.
5. Restore to a separate host or staging environment and test critical services.
6. Only then stop services and reset/rebuild the original VPS after explicit confirmation.

**Status: CODE ARCHIVE IN PROGRESS — VPS RESET NOT AUTHORIZED BY THIS CHECKLIST.**
