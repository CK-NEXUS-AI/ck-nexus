# Capability Resolution and Scoring

Status: architecture contract. This document does not promote any release gate.

## Purpose

CK-NEXUS resolves an intent to a semantic capability first, then selects an implementation. The orchestrator must not import or branch on concrete providers/connectors.

## Resolution pipeline

1. Compile intent into required capability IDs and constraints.
2. Query Capability Registry for lifecycle-eligible candidates.
3. Reject candidates that fail policy, tenant, data-sovereignty, auth, freshness, health, or contract requirements.
4. Compute deterministic eligibility and a bounded preference score.
5. Select a primary candidate and an ordered fallback set.
6. Produce a `capability-decision` record before execution.
7. Re-evaluate after material health/policy/quota changes; never silently expand privileges.

## Hard filters

A candidate is ineligible if any condition is true:

- lifecycle is disabled, quarantined, revoked, or deprecated without explicit compatibility allowance;
- required capability is absent or unvalidated;
- policy decision is deny or approval-required without approval;
- provider-native scopes are insufficient;
- requested data classification violates tenant/region/provider policy;
- health freshness exceeds the configured maximum age;
- cost exceeds a hard user/tenant budget;
- side-effect class exceeds the task grant;
- contract version is incompatible;
- evidence requirements cannot be satisfied.

Hard filters always outrank score.

## Score model

The default normalized score is 0..1:

`score = sum(weight_i * metric_i) / sum(active_weights)`

Recommended dimensions:

- task_fit
- verified_quality
- grounding_or_citation_quality
- historical_success
- health
- latency
- cost_efficiency
- privacy_locality
- quota_headroom
- evidence_completeness

Metrics that are unknown are excluded from scoring rather than treated as perfect. Policy may require a minimum metric for high-impact work.

## Determinism

Given the same registry snapshot, policy hash, health snapshot, task constraints, and scoring profile, ordering must be reproducible. Ties are broken by stable implementation ID, not random choice, unless an explicit experiment policy is active.

## Modes

- `single_best`: choose best eligible implementation.
- `fallback`: choose primary plus ordered alternatives.
- `parallel`: run multiple read-only candidates and verify/compose.
- `council`: assign semantic roles and aggregate evidence.
- `shadow`: execute a non-authoritative candidate without external side effects.
- `canary`: limited real execution under canary policy and explicit blast-radius controls.

## Anti-patterns

- provider name checks in orchestrator;
- score overriding deny/approval;
- rotating to an unapproved account/key because quota is low;
- treating free tier as unlimited;
- auto-promoting a candidate solely because it produced an answer;
- counting duplicate provider features as unique CK-NEXUS skills.

## Required decision evidence

Every selection records capability ID, candidate IDs, rejected candidates with reason codes, policy hash, registry snapshot/version, weights, score breakdown, health age, selected implementation, fallback order, and approval reference if applicable.
