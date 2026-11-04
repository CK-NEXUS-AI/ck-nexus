# CK-NEXUS GitHub File Retention Decisions — 2026-09-04

Status: READ-ONLY AUDIT / NO DELETION AUTHORIZED

## Exact audit subject

- Canonical commit: `b4146db8e23dff49520cbbc9d0194a15bcc5872d`
- Canonical tree: `25d9c74db2b553667ad085172f8ac7beff4146aa`
- Tracked files: 531
- Tracked bytes: 2,828,981
- Remote branches inventoried: 274
- Branch-only unique blobs inspected: 1,444

## Canonical-main retention result

- KEEP: 423
- KEEP_RETAIN_HISTORY: 12
- REVIEW: 85
- ARCHIVE_CANDIDATE: 11
- DELETE_CANDIDATE: 0

No canonical-main file currently has enough evidence for automatic deletion.

## Review decisions

### Keep

The following review classes should remain until a dedicated replacement proves they are unnecessary:

- `.env.*.example` templates — inspected; no OpenAI/GitHub/private-key/AWS secret signature was found.
- empty package `__init__.py` files — empty content is intentional package structure, not junk.
- release/security/gate/backup/restore/VPS scripts — operational evidence paths; retain until their gate consumers are mapped and superseded.
- `requirements-dev.txt`, `pytest.ini`, Docker Compose files, schemas and connector bridge package files — active development/build inputs.
- `demo_evidence/WEB_DEMO_VALIDATION.json` — historical evidence; retain even if later moved under a history/evidence namespace.

### Consolidation candidates — do not delete yet

1. `config/orchestration_patterns.json`
   - exact content duplicate of `orchestration/patterns.json`;
   - runtime packaging explicitly includes `orchestration/patterns.json`;
   - current exact-name search found only the checksum manifest referencing the config copy.
   - Candidate action: prove no dynamic consumer, then consolidate to one canonical copy and update manifests/tests.

2. `migrations/001_email_journal.sql`
   - exact content duplicate of `migrations/postgresql/001_email_gateway.sql` and
     `services/email_gateway/migrations/postgresql.sql`;
   - production code explicitly names `migrations/postgresql/001_email_gateway.sql`;
   - package metadata includes `services.email_gateway/migrations/*.sql`;
   - exact-name search for `migrations/001_email_journal.sql` found only the checksum manifest.
   - Candidate action: verify no glob/installer dependency before consolidation.

3. SQLite email migration copies
   - `migrations/sqlite/001_email_gateway.sql`
   - `services/email_gateway/migrations/sqlite.sql`
   - identical, but top-level runtime and installed-package use cases differ.
   - Keep both until package/runtime migration loading is unified.

4. `UNIFIED_PACKAGE_READY.txt`
   - marker text only;
   - current `package-unified.yml` triggers from branch/workflow, not from this file.
   - Candidate action: verify no external process consumes the marker before archival/removal.

### Historical documentation

The 11 files classified ARCHIVE_CANDIDATE are not deletion candidates. They retain lineage,
validation history or recovery context. Prefer moving them later to a documented
`docs/history/` namespace only after links/checksums/release packaging are updated.

## Exact duplicate groups on canonical main

- 8 empty Python package marker files — KEEP.
- orchestration pattern JSON pair — consolidation review.
- PostgreSQL email migration triple — consolidation review.
- SQLite email migration pair — consolidation review.

## Branch retention

The branch audit found 1,444 unique blobs not present on canonical main:

- KEEP: 1,151
- KEEP_RETAIN_HISTORY: 29
- REVIEW: 255
- ARCHIVE_CANDIDATE: 9
- DELETE_CANDIDATE: 0

Therefore bulk branch deletion is unsafe.

At the audited snapshot, only these non-main branches had zero branch-only unique blobs:

- `agent/unified-control-package`
- `ops/canonical-export-20260904-run`
- `ops/canonical-export-20260904-trigger`
- `post-p0/standards-integration-v1`
- `post-p0/stress-lab-level2-write-activation-gate-v1`

Zero unique blobs is not deletion authorization. PR/workflow/reference state must be checked first.
For example, `agent/unified-control-package` is referenced by the Unified packaging workflow/PR history,
and the Stress Lab branch has PR history.

## Backup snapshot

A branch-only development snapshot ZIP was inspected structurally:

- path: `exports/ck-nexus-development-snapshot-9924b488.zip`
- branch: `backup/ck-nexus-snapshot-2026-08-21`
- archive members: 696
- secret signature categories found by bounded archive scan: none

Keep it as recovery history until a separate backup-retention policy proves a newer verified backup
fully supersedes it.

## Workflow hardening observation

Canonical main has 27 workflow files. 21 currently contain one or more mutable action version refs
such as `actions/checkout@v6` or `actions/upload-artifact@v4`.

This is a hardening priority, not a deletion issue. Production/security-sensitive workflows should
progressively pin action references to reviewed exact commit SHAs.

## Deletion rule

A future deletion requires all of:

1. exact path/blob identity;
2. no active runtime/build/package/test/evidence consumer;
3. no unique branch/recovery value;
4. replacement or archive path documented;
5. tests/security checks after the proposed change;
6. human review before deletion.

Until then: retain.
