# CK-NEXUS Monorepo Migration Plan

Status: PREPARATION_ONLY

Target branch: `arch/monorepo-layered-v01`
Canonical baseline: `45fde79c717b09f8675645aa541a5834ebd4f433`

## Migration rule

Do not restructure canonical `main` while Q10 Deep Security remains incomplete. The existing tree has current Q01-Q09 evidence. Large path moves would make exact-tree evidence stale and increase the review surface before Q10.

## Phase 0 — Architecture freeze

- Record target ownership boundaries.
- Record provider-neutral contracts.
- Record connector lifecycle and credential boundary.
- Add no runtime imports and move no production code.

Exit: architecture docs reviewed; canonical application unchanged.

## Phase 1 — Contract seams

Introduce compatibility interfaces in-place before moving implementations:

- Provider interface
- Connector interface
- Capability registry contract
- Credential lease contract
- Evidence envelope
- AGNES execution request/result contract

Existing imports continue to work through compatibility adapters.

Exit: all current tests and gates remain green on the migration branch.

## Phase 2 — Leaf adapters

Move low-coupling provider and integration adapters first. Preserve old import locations using thin compatibility modules until downstream code is migrated.

Order:

1. providers
2. integrations
3. contracts/schemas
4. observability helpers

No governance or execution kernel move in this phase.

## Phase 3 — Services and cognitive fabric

Move pure decision/orchestration components that do not perform direct external side effects:

- gateway/orchestrator
- cognitive fabric/governor
- consensus/planner/verifier
- registries
- memory/knowledge service façades

Enforce dependency direction: apps -> services/intelligence -> contracts; never reverse-import apps from core layers.

## Phase 4 — AGNES execution kernel

Move AGNES last among runtime-critical components. Preserve fail-closed controls:

- approval
- capability grants
- credential leases
- permission guards
- idempotency
- execution manifest
- evidence
- kill switch
- recovery/checkpoint behavior

No adapter may bypass these controls after migration.

## Phase 5 — Governance and evidence convergence

Consolidate duplicate policy/authority/evidence ownership into one canonical tree. Historical evidence is not moved in a way that changes its content identity; use provenance manifests when relocating release artifacts.

## Phase 6 — Apps and packaging

Move UI/API entrypoints into `apps/` only after internal import seams are stable. Update Docker, Compose, Makefile, CLI, release packaging and deployment paths together.

## Phase 7 — Full verification

A migration release is not eligible for production promotion until fresh evidence is generated for the new exact tree:

- dependency closure and frozen install
- lint/compile/test regression
- live PostgreSQL/Redis/idempotency
- governance binding
- Codex Security Deep Security Scan
- validated fixes/regression
- isolated buyer staging
- observability failure-injection receipt
- destructive restore drill on disposable staging
- release provenance/freshness
- final GO/NO-GO

## Connector registry snapshot policy

Runtime connection state must be recorded separately from source architecture. A connector is not `HEALTHY` merely because code exists. It requires a live authenticated probe in the current runtime.

Current verified connector categories should be represented with evidence timestamps and scopes. OAuth refresh is permitted only through provider-supported flows for owner-authorized credentials. Credential rotation must never create accounts, mint unauthorized keys, or evade provider quotas.

## Rollback strategy

Each migration phase must be independently revertible. Avoid mixed commits that both move files and change behavior. Recommended commit sequence per component:

1. add target package + compatibility tests
2. copy/move implementation without semantic changes
3. redirect imports
4. run regression
5. remove compatibility shim only after dependents converge

Never force-push canonical history to perform the migration.
