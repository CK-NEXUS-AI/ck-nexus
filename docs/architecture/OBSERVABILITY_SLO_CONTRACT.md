# Observability and SLO Contract

Status: architecture contract. This does not establish Q13 PASS.

## Purpose

CK-NEXUS observability must answer whether users and autonomous workflows are receiving correct, timely and verifiable service. Metrics are not release evidence by themselves; they become evidence when bound to a subject, method, time window and operator-visible receipt.

## Signals

Four correlated signal families are required:

- metrics: rates, latency, saturation, queue depth, errors and business-integrity indicators;
- traces: task -> capability decision -> AGNES node -> provider/connector -> verifier spans;
- logs: structured diagnostic events with tenant-safe redaction;
- domain events: approvals, policy decisions, connector state, reconciliation, incidents, recovery and release gates.

All signals carry correlation/task IDs where applicable. Sensitive payloads and credentials are excluded or redacted.

## SLI classes

Minimum platform SLIs:

- request availability and latency;
- AGNES task verified-success rate, not merely executor 2xx rate;
- unknown-commit-state rate;
- reconciliation age/failure rate;
- connector/provider healthy-and-fresh availability;
- approval queue age;
- event backlog/dead-letter rate;
- durable journal lag;
- evidence production latency/freshness;
- security veto and policy-denial counts;
- memory/knowledge ingestion validation/quarantine rate.

## SLO profile

An SLO declares service/capability scope, tenant/environment scope, SLI query/definition, objective, evaluation window, minimum traffic/sample requirements, error budget, alert policy and exclusions. No-data windows are `INSUFFICIENT_DATA`, not automatically PASS.

## Burn alerts

Use multi-window burn-rate or equivalent bounded alerts for production SLOs. Thresholds must be justified per service. A single static threshold may remain for development checks but does not by itself prove Q13 readiness.

## Alert delivery evidence

An alert rule existing in source is implementation evidence only. Q13 requires controlled failure injection or a naturally occurring safe test condition plus captured routing/operator receipt, correlation IDs, timing and recovery evidence. `scripts/gate_observability.py` correctly remains fail-closed when no operator alert receipt is supplied.

## Cardinality and privacy

Do not put raw user IDs, email addresses, URLs with secrets, prompt text, document contents, tokens or arbitrary exception payloads in metric labels. High-cardinality identifiers belong in traces/logs with tenant-safe access controls.

## UI semantics

The Command Center distinguishes `HEALTHY`, `DEGRADED`, `UNHEALTHY`, `UNKNOWN`, and `INSUFFICIENT_DATA`. Stale telemetry is not rendered as current green health.

## Q13 boundary

This contract and static alert rules are preparation only. Q13 remains incomplete until isolated staging demonstrates collection, alert routing, operator receipt, diagnosis correlation and recovery visibility under the required failure scenarios.
