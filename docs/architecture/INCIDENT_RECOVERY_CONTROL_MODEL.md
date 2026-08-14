# Incident and Recovery Control Model

Status: architecture contract.

## Incident purpose

An incident groups related failures, degraded dependencies, security vetoes, unknown commit states, or SLO breaches into an operator-visible control object.

## Severity

- `INFO`: no action required.
- `MINOR`: limited degradation, automatic mitigation available.
- `MAJOR`: material user/workflow impact.
- `CRITICAL`: security, financial, data-integrity or production-control risk requiring immediate containment.

## Lifecycle

`OPEN -> TRIAGED -> MITIGATING -> MONITORING -> RESOLVED -> CLOSED`

A resolved incident may reopen if the same condition recurs within a correlation window.

## Recovery actions

Recovery commands include retry-after-reconcile, fallback, pause workflow, isolate connector/provider, compensation, restore from checkpoint/backup, roll back release, rotate/revoke credential (owner-controlled), and manual remediation.

Each recovery action is a normal governed capability: policy, risk, approval, idempotency, execution receipt and evidence apply.

## Unknown commit state

An unknown external mutation outcome is an incident-worthy integrity condition. Reconciliation precedes retry. The UI must display uncertainty rather than claiming failed/successful prematurely.

## Kill switch

Governance owns kill-switch authority; AGNES enforces it. Kill switch can target global, tenant, workflow, capability, implementation/provider or environment scopes. It blocks new dispatch and defines handling of already-running work.

## Restore/rollback

Destructive restore or production rollback requires isolated target validation, explicit authority and evidence. Backup existence is not equivalent to restore readiness; restoration must be drilled and verified.

## Evidence closure

Incident closure requires timeline, impact, root/likely cause, containment actions, recovery outcome, verifier results, remaining uncertainty, evidence refs and follow-up work where applicable.
