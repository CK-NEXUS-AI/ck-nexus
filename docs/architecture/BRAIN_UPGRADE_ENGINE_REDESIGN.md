# Brain Upgrade Engine Redesign

Status: architecture contract replacing unverified `absorb skills` semantics.

## New model

The Brain Upgrade Engine is a governed capability/knowledge discovery and evaluation service, not a mechanism for copying another model into CK-NEXUS.

## Cycle

1. Observe approved sources and installed/connected runtimes.
2. Compute delta against current CK semantic registry and knowledge graph.
3. Create source-backed knowledge claims and capability candidates only for meaningful deltas.
4. Validate schema/provenance/licensing/policy.
5. Deduplicate against existing semantic capability and knowledge claims.
6. Run safe contract/evaluation lanes in sandbox/shadow mode.
7. Produce scorecards and evidence.
8. Leave candidates quarantined/candidate unless promotion policy is satisfied.
9. Emit a human-readable change report: new, improved, duplicate, rejected, stale.

## What counts as upgrade

Examples:

- new verified connector operation;
- better implementation of an existing capability;
- newly validated public/owner-approved knowledge;
- better routing/evaluation statistics;
- new workflow/skill with a tested contract;
- improved local model/provider availability.

## What does not count

- duplicate database rows;
- provider marketing claims without verification;
- generic statements like `advanced reasoning` with no test/contract;
- inaccessible hidden prompts/weights;
- token/key distribution to unrelated services;
- a successful OAuth connection by itself.

## Continuous mode

Continuous mode schedules discovery/evaluation only. It cannot bypass approvals, create paid accounts/resources, widen scopes, rotate keys to evade quota, deploy production, or promote its own code.

## Metrics

Track observed sources, candidate delta, dedupe ratio, validation pass rate, quarantine reasons, evaluations, promoted capabilities, regressions, provenance coverage and stale objects.
