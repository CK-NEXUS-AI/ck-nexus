# CK-NEXUS Gen4 Fusion — Post-P0 Migration Plan v0.2

## Track A — production closure remains isolated

Do not alter the frozen production subject until Q10 → Q11 → Q12 → evidence reconciliation → Final Production Package is complete and human release approval is obtained.

## Track B — Gen4 integration after P0

1. Port `EvidenceRecord` + append-only provenance/freshness rules into canonical core.
2. Add evidence read API and migrate Dashboard cards off hard-coded values.
3. Replace Connect-All simulation with real backend lifecycle transitions.
4. Bind OAuth/provider results to evidence IDs and credential references.
5. Introduce Capability Lease + Approval objects.
6. Route every external write through `ExecutionEnvelope` authorization.
7. Add independent effect verification and false-completion detection.
8. Compile public/sales/release claims from evidence state.
9. Add MCP/A2A protocol gateway and agent identity/delegation plane.
10. Add Skill SBOM, transitive dependency lock, provider economics/sovereignty registry.

## Invariants

- LOCAL PASS ≠ STAGING PASS ≠ PRODUCTION PASS.
- STATIC_CONFIG ≠ RUNTIME_VERIFIED.
- SPEC_ONLY ≠ IMPLEMENTED.
- DISCOVERED ≠ AUTHORIZED.
- CONNECTED ≠ WRITE_AUTHORIZED.
- TEST_PASS ≠ RELEASE_PASS.
- Historical status never overrides current canonical evidence.
- Models/agents may propose actions but never self-authorize mutations.
