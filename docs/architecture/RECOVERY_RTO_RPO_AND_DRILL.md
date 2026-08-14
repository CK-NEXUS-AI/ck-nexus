# Recovery, RTO/RPO, and Drill Contract

Status: architecture contract. This does not establish Q14 PASS.

## Purpose

Recovery readiness is proven by restoring service/data into an isolated target and verifying business invariants. Having a backup file or rollback command is not sufficient.

## Recovery objectives

Each stateful service defines:

- RPO: maximum acceptable data-loss window;
- RTO: maximum acceptable time to restore verified service;
- recovery tier: critical, important, best-effort;
- authoritative stores and derived/rebuildable stores;
- backup/replication method;
- restore dependency order;
- validation probes and business invariants.

Targets are deployment policy, not universal constants.

## Drill lifecycle

`PREPARED -> TARGET_ISOLATED -> BACKUP_SELECTED -> RESTORING -> VALIDATING -> VERIFIED|FAILED|BLOCKED -> CLEANUP`

A drill records source backup/artifact digests, clean target identity, environment isolation evidence, start/end times, restore commands/tool versions, service versions, validation results, RTO/RPO observations and cleanup outcome.

## Isolation

Destructive restore is permitted only in an explicitly isolated staging/recovery target. The seller master/current working environment is never the target by default. Network/credential policy must prevent restored staging from accidentally sending production email/messages/payments/webhooks.

## Validation

Minimum validation after restore:

- database/store integrity and expected schema/migrations;
- application health;
- critical read path;
- bounded write/idempotency path where safe;
- queue/outbox safety and no unintended delivery;
- durable action journal consistency;
- tenant/access boundary checks;
- evidence/telemetry availability;
- backup subject/version matches intended recovery point.

## Recovery types

- data restore from backup;
- service rollback to prior artifact;
- configuration rollback;
- connector/provider isolation/failover;
- event replay/reconciliation;
- compensation for external side effects.

These are distinct capabilities with distinct risk and evidence.

## Q14 proof

Q14 requires a real isolated drill receipt for the release candidate context, not this document. The drill must show the target was clean/isolated, restoration actually occurred, invariants passed, measured RTO/RPO were evaluated and residual uncertainty is explicit.
