# Approval and Authority Model

Status: architecture contract.

## Principle

Approval is a scoped, expiring authorization for a specific proposed action. It is not a global bypass switch.

## Authority inputs

A decision evaluates principal identity, tenant/workspace, role/attributes, requested capability, target, data classification, environment, risk, side-effect class, policy hash, current system state, credential lease class, and evidence/precondition summary.

## Approval states

`REQUESTED`, `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`, `REVOKED`, `CONSUMED`, `SUPERSEDED`.

Only `APPROVED` and still-valid requests may issue an execution grant. One-time approvals become `CONSUMED` after the authorized operation claim is accepted.

## Binding

An approval is cryptographically/hash-bound or logically bound to:

- approval ID
- tenant
- actor/requester
- exact capability/action
- target fingerprint
- request/plan hash
- risk/side-effect class
- environment
- policy hash/version
- optional maximum cost
- optional maximum attempts
- validity window

Material change to plan, target, permissions, environment, cost ceiling, or policy requires a new approval.

## Approval classes

Suggested classes:

- `NONE`: no human approval required under policy.
- `OPERATOR`: authorized operator approval.
- `ADMIN`: tenant/workspace admin approval.
- `OWNER`: owner-only approval.
- `DUAL_CONTROL`: two distinct authorized principals.

Production, billing, destructive security, broad permission elevation, credential creation/rotation, and irreversible operations default to owner or stronger policy.

## Least authority

Approval never reveals credentials. It authorizes a bounded CredentialBroker lease/capability grant. The executor receives only what is required for the operation.

## UI requirements

Approval UI shows exact verb, target, risk, expected side effect, reversibility/compensation, environment, cost/quota impact, credential class, validation/test summary, evidence, and expiry. Buttons use explicit verbs rather than Yes/No.

## Revocation and race safety

Approval consumption uses atomic compare-and-set/lease semantics. Revoked/expired approvals fail closed. A cancellation or kill-switch event may invalidate an unconsumed grant.

## No approval laundering

An approved low-risk/read operation cannot be reused by an agent to perform a write. Chained actions require each consequential node to be covered by its own policy/grant or a narrowly defined approved plan envelope.
