# CK-NEXUS Engineering Standards

Status: DEVELOPMENT STANDARD / NOT A PRODUCTION APPROVAL

## 1. Core principles

- Optimize for readability before cleverness.
- Keep structures consistent and machine-checkable.
- Prefer direct access paths over deep indirection.
- Reuse canonical components before creating new ones.
- Every change must be reversible, testable, and attributable.
- Development evidence never upgrades Production status by itself.

## 2. Naming

Naming follows the host language rather than forcing one style everywhere.

| Surface | Rule | Example |
| --- | --- | --- |
| Docs/folders | kebab-case | `agent-security/` |
| Python modules/functions | snake_case | `check_permission()` |
| JS/TS variables/functions | camelCase | `checkPermission()` |
| Classes/types | PascalCase | `SecurityPolicy` |
| Constants | UPPER_SNAKE_CASE | `DEFAULT_TIMEOUT_MS` |

Names describe purpose and direction. Avoid opaque abbreviations and numbered names such as `check1`.

## 3. Data contracts

Canonical records should expose stable identity, type, time, provenance, version, and payload.

```json
{
  "id": "unique-id",
  "type": "record-type",
  "timestamp": "2026-09-03T12:00:00Z",
  "metadata": {"source": "ck-nexus", "version": "1"},
  "data": {}
}
```

Use ISO 8601 timestamps. Use descriptive string states. Use `null` for an absent optional value unless a schema explicitly defines another representation.

## 4. Repository organization

Organize by responsibility, not author or date. One file should have one primary responsibility. Do not reorganize stable packages merely to match a cosmetic tree; migrations require a measured benefit and compatibility plan.

Every new top-level subsystem should include a short README or equivalent index explaining purpose, entrypoints, ownership, tests, and security boundaries.

## 5. API contracts

APIs return truthful HTTP status codes and a stable response envelope where applicable:

```json
{
  "success": true,
  "code": "STATUS_OK",
  "message": "Operation completed",
  "data": {},
  "error": null
}
```

Do not expose secrets, internal stack traces, or fields not required by the caller. Large result sets must support bounded pagination or streaming.

## 6. Evidence and change control

Every capability follows: DISCOVERED -> CONNECTED -> EXECUTED -> VERIFIED.

Candidate adoption follows: Search-first -> Delta-only -> Reuse/Dedup -> Benchmark -> Security review -> Independent verification -> Canonical adoption.

A candidate that does not improve the measured baseline and adds no required capability is rejected. Frozen Q10 evidence and Production gates are separate from development work.
