# CK-NEXUS Platform Scaffold

This branch introduces the first code-level scaffold for the expanded monorepo architecture without moving or deleting existing production code.

## Migration rule

Existing `creator_app/`, `app/`, contracts, evidence and CI remain authoritative until each new service is bound, tested and explicitly promoted. This is an additive migration, not a history rewrite.

## Target domains

- `services/cognitive_fabric/` — provider-neutral cognitive contracts and routing
- `services/cognitive_governor/` — model-to-authority policy boundary
- `intelligence/intent_graph/` — normalized intent representation
- `intelligence/task_dag/` — dependency-aware task planning
- `governance/policies/` — provider-neutral policy decisions
- `observability/telemetry/` — correlation and trace context
- `evidence/runtime/` — structured runtime evidence contracts

## System flow

```text
Input
  -> Gateway
  -> Intent Graph
  -> Cognitive Governor
  -> Cognitive Fabric / Model Router
  -> Task DAG
  -> Capability / Authority checks
  -> AGNES Execution Kernel
  -> Verification
  -> Evidence / Audit
  -> Canonical State
```

## Invariants

1. Models propose; CK-NEXUS owns authority and canonical state.
2. Unknown risk fails closed.
3. Existing AGNES Execution Kernel remains the side-effect execution authority.
4. Provider selection is replaceable and capability-driven.
5. Correlation IDs and source identity must survive every boundary.
6. Runtime evidence is first-class and must be tied to source/environment identity.
7. New modules are not production-authoritative until integration gates pass.

## Next implementation slices

1. Bind `CognitiveGovernor` to existing R32/R32.1 authority policies.
2. Add provider adapters behind `CognitiveProvider`.
3. Compile Intent Graph into Task DAG.
4. Bind Task DAG execution nodes into AGNES skills/capabilities.
5. Emit OpenTelemetry-compatible spans and runtime evidence.
6. Add integration tests covering governor -> router -> AGNES boundaries.
7. Promote one capability at a time through Q-gates; do not bulk-replace existing runtime.
