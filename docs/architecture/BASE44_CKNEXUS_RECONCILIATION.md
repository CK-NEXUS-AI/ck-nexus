# Base44 / Solas to CK-NEXUS Reconciliation

Status: architecture contract based on read-only live observations. No Base44 records are modified by this design.

## Authority precedence

For connection state:

1. live Base44 connector API observation;
2. fresh provider-native probe if available and authorized;
3. Base44 connector/entity cache;
4. historical/manual claims.

For CK capability validity:

1. CK contract + validation evidence;
2. normalized live runtime observation;
3. external entity claim.

External `brain` counters never create authoritative CK capabilities by themselves.

## Observed integrity classes

- `MATCH`: cache and live observation agree.
- `LIVE_NEWER`: live API supersedes cache.
- `CACHE_ONLY`: cache claims an object not observed live.
- `LIVE_ONLY`: live object lacks cache record.
- `MALFORMED`: required external record fields are null/invalid.
- `CONFLICT`: materially incompatible observations.
- `STALE`: freshness window exceeded.

## Current Base44 examples

The federation design observed a live connector catalog and a separate `CkNexusConnector` cache. A cache record may be pending while live active-count excludes it. Skill/memory rows with missing semantic IDs are `MALFORMED` and enter quarantine; they are not counted as CK-NEXUS capabilities/memory.

## Reconciliation cycle

1. Collect read-only external observations.
2. Validate external observation schema.
3. Normalize IDs/scopes/capabilities.
4. Compare live observations to external cache and CK registry.
5. Produce reconciliation records and conflicts.
6. Quarantine malformed/ambiguous candidates.
7. Update CK materialized registry only through validated candidate promotion rules.
8. Emit evidence and metrics.

## No destructive cleanup by default

CK-NEXUS does not delete or rewrite Solas/Base44 records merely because they are malformed. Cleanup is a separate mutation requiring owner authorization, backup/export strategy, and evidence.

## Connector scope mapping

Provider-native scopes are observations. A semantic mapper derives CK capability candidates; it never assumes a scope string is sufficient proof that an API operation works. Capability verification uses contract tests or safe live probes.

## Drift handling

When live state changes (revocation, reauth, scope reduction), CK registry state is downgraded immediately or on the next freshness-bound observation. A stale `ACTIVE` cache cannot keep an execution lane eligible.
