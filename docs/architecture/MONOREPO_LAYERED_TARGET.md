# CK-NEXUS Layered Monorepo Target Architecture

Status: TARGET / MIGRATION PLAN ONLY

Canonical baseline: `45fde79c717b09f8675645aa541a5834ebd4f433`

This document defines the target repository shape for CK-NEXUS without changing the current canonical runtime or Q01-Q10 evidence lineage. The migration must happen incrementally on dedicated branches and must not be merged until release-gate provenance is intentionally refreshed.

## Principles

1. One authoritative directory per responsibility. Avoid duplicate `services/`, `governance/`, `evidence/`, or integration roots.
2. Provider-neutral orchestration. Core orchestration depends only on a shared provider contract, never a vendor SDK directly.
3. AGNES is the execution plane. Model/provider outputs cannot directly mutate external systems.
4. Governance is fail-closed. Approval, risk, quota, credential, idempotency, and kill-switch checks precede side effects.
5. Evidence is first-class. Every high-impact execution and release gate binds evidence to immutable source identity, policy identity, environment, and execution identity.
6. Credentials remain brokered and owner-authorized. No automatic account/key creation, quota-evasion rotation, or secret export.

## Target top-level layout

- `apps/` — control hub, admin console, buyer demo, API gateway, dashboard
- `services/` — gateway, orchestrator, cognitive fabric/governor, consensus, verifier, registries, memory, knowledge, evidence, audit, integration service
- `agnes/` — runtime, planner, dispatcher, executor, scheduler, workflow, recovery, checkpoints, skills, ledger, execution guards
- `intelligence/` — intent graph, task DAG, reasoning, capability/model routers, conflict resolution, learning
- `providers/` — common provider contract plus vendor adapters
- `integrations/` — connector adapters, MCP/A2A/webhooks and external platform integrations
- `governance/` — policies, authority, approvals, risk, quotas, compliance, kill switch
- `contracts/` and `schemas/` — stable cross-layer interfaces and validation schemas
- `data/` — PostgreSQL, Redis, vector, graph, object storage, migrations, fixtures
- `observability/` — telemetry, metrics, traces, logging, dashboards, alerts
- `evidence/` — runtime, release, security, recovery, provenance, gates
- `tests/` — unit, integration, regression, e2e, performance, security
- `docs/` — architecture, API, deployment, governance, providers, release
- `releases/` — release metadata and immutable packaging outputs only

## Provider interface boundary

Every provider adapter must implement a common contract equivalent to:

- capability discovery
- health/availability
- normalized request execution
- normalized response/evidence metadata
- cost/quota metadata when provider exposes it
- data-policy metadata
- cancellation/timeouts

Provider adapters must not receive direct execution authority over external side effects. They produce proposals/results consumed by CK-NEXUS governance and AGNES.

## Migration order

Phase A — inventory and aliases only
- Map current files/modules to target ownership.
- Add compatibility imports/adapters where needed.
- No destructive moves.

Phase B — contract extraction
- Extract provider, tool, connector, evidence, policy, and execution contracts.
- Add dependency-direction tests.

Phase C — execution boundary consolidation
- Consolidate AGNES approval, capability, credential, idempotency, evidence, permission, and kill-switch enforcement.
- Preserve existing fail-closed behavior.

Phase D — integration/provider moves
- Move provider-specific and connector-specific code behind contracts.
- Keep compatibility shims until regression suite proves parity.

Phase E — apps/services split
- Move public/API/UI entry points after internal contracts stabilize.

Phase F — evidence and release refresh
- Re-run exact-tree CI, live backend gates, security scan, staging, observability, recovery, provenance, and final GO/NO-GO on the new immutable source identity.

## Current gate constraint

Q01-Q09 are tied to the current canonical lineage. Q10 Deep Security remains the earliest incomplete production gate. Therefore this architecture branch must remain non-canonical and must not be used to claim production readiness until the complete Q10-Q16 sequence is rerun against the migrated immutable tree.

## Connector policy

Connector registry states must distinguish at least:

- `AVAILABLE_UNBOUND`
- `AUTH_REQUIRED`
- `CONNECTED_READ_ONLY`
- `CONNECTED_WRITE_SCOPED`
- `UNAVAILABLE_IN_RUNTIME`
- `DEGRADED`
- `REVOKED`

A connector is never marked connected from historical chat text alone; current runtime evidence is required.
