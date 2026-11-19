# Skill Foundry Pipeline — Integration Slice

Date: 2026-11-19

## Implemented

The first integration bridge now connects three existing CK-NEXUS boundaries:

1. **Idea Engine** — the selected idea must exist in the supplied IdeaGraph, must not be archived, and must reference the research artifact or one of its sources.
2. **Research Repository** — the artifact is loaded by both tenant ID and artifact ID. Only `READY_FOR_ANALYSIS`, `ready_for_analysis=true`, `MEASURED_NOT_VERIFIED` artifacts are eligible. `VERIFIED` is never inferred or granted.
3. **Knowledge Repository** — source and claim records are reloaded inside the requested tenant scope. Missing, cross-tenant, revoked, or out-of-artifact claim/source references block draft creation.
4. **Evidence Ledger** — draft registration and the Idea → Research → Skill lineage link are written as separate append-only hash-chained events.

## Permission boundary

- The caller must provide an explicit permission-basis value for every research source. The pipeline does not infer rights from a URL, public visibility, or source type.
- Permission values are restricted to the Skill Foundry allowlist. This records an asserted basis; it is not legal verification.
- Source fingerprints hash the canonical source-record metadata, not the original page bytes. The field is therefore named `source_record_sha256`.
- Revoked sources are rejected before any Skill Foundry event is written.

## Generated proposal

The pipeline derives a stable skill ID from the Idea Engine node, creates object input/output schemas, and adds four synthetic evaluation fixtures (positive, negative, boundary, adversarial). The new skill remains `QUARANTINED`.

The evidence ledger records:
- `skill_foundry.draft_registered`
- `skill_foundry.research_linked`

The research link records tenant, artifact, idea, skill, source IDs, claim IDs, and the registration event hash. It explicitly records `activation_allowed=false`.

## Not done / not claimed

- No live PostgreSQL/Knowledge database was contacted in this implementation test.
- No existing production workflow or API route invokes this pipeline yet.
- No model-generated execution, runtime skill installation, activation, marketplace publication, or production deployment occurs.
- Database-level tenant isolation, authentication and authorization for a future API entrypoint still need separate integration verification.
- Passing the current unit/regression tests does not establish production readiness.

## Verification

The focused verification command covers Skill Foundry contracts and pipeline, Research Persistence V1 and its bridge, canonical Idea Engine, control-plane task store, and universal command protocol. Results are recorded in the commit and CI should independently repeat them.
