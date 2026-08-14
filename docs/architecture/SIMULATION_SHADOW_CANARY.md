# Simulation, Shadow, and Canary Execution

Status: architecture contract.

## Purpose

Increase autonomy only after behavior is measured under bounded risk.

## Simulation

Simulation operates on synthetic, replayed, or redacted snapshots with no external side effects. It predicts candidate plans, policy decisions, costs, latency, failure modes, and expected evidence. Simulation results are hypotheses, not proof of real-world success.

## Shadow mode

Shadow execution observes real task inputs under policy but cannot perform external mutations. It may run alternative planners/models/verifiers and compare their decisions to the authoritative lane. Sensitive data constraints still apply.

## Canary mode

Canary permits bounded real execution only for capabilities explicitly eligible for canary. Controls include tenant/user allowlist, percentage/volume cap, time window, maximum risk class, maximum cost, side-effect allowlist, automated rollback/disable trigger, and required observability/evidence.

## Promotion criteria

Promotion requires a defined sample size/window and thresholds for contract correctness, verified success, safety/policy violations, latency, cost, reconciliation anomalies, and incident rate. Zero evidence never counts as success.

## Automatic demotion

A canary/stable implementation may be automatically disabled or demoted on security veto, contract breach, rising unknown-commit-state rate, repeated reconciliation failure, health/SLO breach, or revoked dependency/provider state. Demotion is safer than self-repair that widens permissions.

## Comparison artifacts

Shadow/canary comparisons store normalized task class, implementation IDs, policy hash, outputs/effects fingerprints, verifier results, scorecard, anomalies, and evidence references. Raw sensitive inputs are minimized/redacted.
