# Base44 Data Repair and Migration Plan

Status: plan only. No Base44 records are modified without separate owner authorization.

## Observed issue

Read-only inspection found Solas `CkNexusSkill` and `CkNexusMemory` rows whose semantic identity/content fields are null. These rows cannot be treated as valid CK-NEXUS skills/memories.

## Safe migration phases

### Phase 0: freeze authority

Mark external counters/rows as non-authoritative in CK federation. Continue using live connector API for connector state.

### Phase 1: export/snapshot

Before any repair, export entity schemas and records or create an equivalent recoverable checkpoint. Record counts and hashes where possible.

### Phase 2: classify

Classify each row as `VALID`, `RECOVERABLE`, `EMPTY_PLACEHOLDER`, `DUPLICATE`, `CONFLICT`, or `UNKNOWN` using schema fields, creation batch/service identity, provenance and any available external source.

### Phase 3: reconstruct candidates

Only if source provenance exists, reconstruct valid skill/memory candidates into a new versioned entity/schema or CK-side import staging area. Never invent missing content based solely on row ID.

### Phase 4: verify

Validate IDs/contracts/provenance, deduplicate, evaluate skills, and verify memory/knowledge source binding.

### Phase 5: cutover

Switch reads to validated normalized records. Keep malformed legacy rows quarantined/excluded.

### Phase 6: optional cleanup

Physical delete/archive of legacy Base44 rows is a separate destructive action requiring explicit owner authorization after backup/recovery verification.

## Schema evolution

Future external records should require semantic IDs and provenance at create time, use validation constraints where supported, avoid default-empty records, and separate counters from source-of-truth records.
