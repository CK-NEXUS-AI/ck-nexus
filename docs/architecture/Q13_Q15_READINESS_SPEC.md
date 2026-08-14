# Q13-Q15 Readiness Specification

Status: PREP_ONLY. Q10 remains the earliest incomplete gate; this document cannot promote Q13-Q15.

## Q13 Observability readiness

Required staging evidence after Q10-Q12:

1. telemetry endpoint/collector healthy;
2. core SLI observations available for staging;
3. controlled failure injection for selected API/task/queue/dependency scenario;
4. alert rule fires within bounded time;
5. routed notification is captured by the intended operator channel;
6. incident/correlation data allows diagnosis from alert to task/dependency;
7. recovery clears/de-escalates the condition and is observable;
8. evidence bundle binds staging identity, source/artifact subject and alert receipt.

Existing `observability/alert_rules.yaml`, `scripts/p0_observability_check.py` and `scripts/gate_observability.py` are implementation/preflight inputs, not sufficient live proof.

## Q14 handoff

Observability must cover backup/restore and rollback drills with task/incident/evidence correlation. Q14 destructive staging restore remains owner-approved and isolated.

## Q15 provenance/freshness readiness

After Q10-Q14 pass:

1. freeze final candidate subject digest;
2. enumerate required gate evidence for exactly that subject;
3. evaluate freshness/invalidation for every artifact;
4. mark missing/stale/subject-mismatch evidence fail-closed;
5. generate immutable evidence manifest and hashes;
6. generate delivery/release status from evidence, not vice versa;
7. independently verify package/source/artifact digest relationships;
8. only then feed Q16 GO/NO-GO.

## Prohibited shortcut

Do not refresh old evidence timestamps, copy PASS labels between subjects, or weaken exact-tree checks to make architecture branches green. Architecture-only files should be located outside the frozen runtime subject when appropriate, as done for `contracts/test-vectors/`.
