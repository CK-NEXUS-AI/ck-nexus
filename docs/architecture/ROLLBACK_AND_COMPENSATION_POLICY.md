# Rollback and Compensation Policy

Status: architecture contract.

## Distinction

Rollback changes CK-NEXUS-owned deploy/config/data state toward a known prior version. Compensation performs a new external action intended to mitigate a prior side effect. Compensation is not assumed to undo history perfectly.

## Release rollback

A release rollback plan declares previous known-good artifact digest, schema compatibility, migration reversibility/forward-fix strategy, configuration/policy compatibility, traffic-switch method, health checks, data-loss risk, required approval and maximum rollback window.

## Database changes

Irreversible destructive migrations require stronger change control and backup/recovery evidence. Application rollback is unsafe if the old application cannot read the new schema; schema compatibility is verified explicitly.

## External compensation

Examples include issuing a refund, cancelling a draft/order where provider semantics allow, posting a corrective message, or reverting a created resource. Every compensation uses its own capability, authorization, idempotency and execution receipt.

## Automatic actions

Automatic rollback/disable is permitted only within preauthorized canary/recovery policy and bounded blast radius. Security veto may disable a capability/provider without executing a destructive restore.

## Verification

Rollback/compensation success requires observed resulting state and verifier evidence. Command success alone is insufficient.
