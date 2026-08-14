# Backup Integrity and Restore Contract

Status: architecture contract.

## Backup set

A backup set may contain source/config snapshot where appropriate, PostgreSQL/database dump, SQLite/local state, object-store data, event/journal data, required migration/schema metadata and a manifest. Secrets are not copied into general backup bundles unless a dedicated encrypted secret-backup policy explicitly governs them.

## Manifest

Backup manifest includes backup ID, tenant/environment scope, created_at, source/artifact subject, store identifiers, consistency method, included/excluded components, per-file/object digests, tool versions, encryption/key reference where applicable, retention class and verification state.

## Consistency

A backup must state whether it is crash-consistent, transaction-consistent, application-coordinated, snapshot-based or logically exported. Cross-store consistency limitations are explicit.

## Integrity verification

Creation-time checksums detect corruption but do not prove restorability. Verification levels:

- `DIGEST_ONLY`
- `FORMAT_VALIDATED`
- `RESTORE_TESTED`
- `BUSINESS_VERIFIED`

Release recovery readiness requires the level defined by policy; for Q14 the relevant restore path must reach business-verified evidence in isolated staging.

## Selection

Recovery point selection considers backup freshness, subject/schema compatibility, corruption status, retention and RPO target. Newest does not automatically mean safest if integrity is unknown.

## Secret and privacy safety

Backups inherit tenant/data classification. Storage, encryption, access, retention and deletion policies apply. Restore logs/evidence redact sensitive data and secret values.

## Existing script relationship

`scripts/backup.sh` currently creates a source archive, optional SQLite backup, optional PostgreSQL dump, SHA256SUMS and BACKUP_ID. That is useful creation evidence, but `POSTGRES_BLOCKED.txt` explicitly means a complete database backup was not captured and cannot be interpreted as recovery-ready PASS.
