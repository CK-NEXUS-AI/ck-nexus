# Cognitive Mode Selection

Status: architecture contract.

## Inputs

Mode selection considers required semantic capabilities, task complexity, uncertainty, consequence/risk, evidence/grounding requirement, latency deadline, budget, privacy/locality, worker health and historical evaluation.

## Default behavior

Use the least complex mode expected to meet the quality requirement:

- simple/low uncertainty -> SINGLE_BEST;
- transient provider risk -> FALLBACK;
- high-value read-only synthesis -> PARALLEL/COUNCIL when budget permits;
- adversarial/security/design review -> COUNCIL with independent reviewer role;
- material unresolved disagreement -> bounded DEBATE or user clarification;
- new worker evaluation -> SHADOW before canary/promotion.

## Bounded execution

Council/debate specifies maximum workers, rounds, total cost, deadline and stopping criteria. A worker cannot recursively spawn unbounded workers.

## Diversity

Diversity is semantic/evidence diversity, not just vendor count. Running five near-identical models on the same unsupported source does not create independent evidence.

## Fallback

Fallback uses already-authorized semantically compatible workers and preserves data policy/output/evidence constraints. Quota exhaustion does not trigger account/key creation or policy downgrade.
