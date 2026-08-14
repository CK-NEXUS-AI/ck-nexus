# Retention and Forgetting Policy

Status: architecture contract.

## Principle

`never_forget` is not a production retention strategy. CK-NEXUS balances continuity with privacy, deletion, data minimization, correctness and user/tenant policy.

## Retention classes

- `EPHEMERAL`: process/task temporary; deleted after purpose/window.
- `SESSION`: valid for a bounded user/session context.
- `OPERATIONAL`: retained for workflow continuity/audit-defined period.
- `LONG_TERM`: explicitly justified durable memory/knowledge.
- `USER_PINNED`: user explicitly requests retention, subject to policy/legal constraints.
- `LEGAL_HOLD`: governed retention that normal deletion cannot override without authorized legal/process action.

## Forgetting

Forgetting may mean deletion, redaction, de-indexing, expiration, confidence decay, supersession, or archival. Semantic/vector indexes must be updated when source content is deleted or access is revoked.

## Access revocation

If a connected source is disconnected/revoked, future retrieval obeys connector/source retention policy. Cached material is not assumed reusable forever; source authorization and data policy determine retention.

## Corrections

Corrections create a new validated claim/version and supersede stale knowledge. Audit metadata may retain hashes/references without preserving sensitive deleted content.

## User controls

Command Center should expose retention class, source, age/freshness, tenant scope, reason retained, and delete/forget actions where policy permits. Destructive bulk deletion requires explicit confirmation/authority.
