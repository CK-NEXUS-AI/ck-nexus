# Proof-Carrying Execution

Status: SPEC_ONLY

Proof-Carrying Execution (PCE) makes every impactful AGNES action carry the authorization, policy, contract, idempotency, and evidence context required to verify why the action was allowed and what actually happened.

## Execution packet

Before side effects, AGNES constructs an immutable ExecutionPacket containing:

- execution_id
- intent_id
- task_id
- capability_id
- plugin_id/version
- actor/tenant/environment
- policy decision id/hash
- risk classification
- approval grant when required
- credential lease reference (never raw secret)
- input contract/version/hash
- idempotency key
- expected side effects
- verification requirements
- timeout/retry/compensation policy
- evidence destination

The packet is signed or integrity-bound by the control plane before entering the execution adapter.

## Execution receipt

The adapter returns an ExecutionReceipt containing:

- packet hash
- start/end timestamps
- target/resource identifiers
- normalized result
- provider request/reference ids where safe
- side-effect status
- idempotency outcome
- verification artifacts
- error classification
- compensation availability
- provenance links

Receipts are append-only. Corrections are new records referencing superseded records.

## State machine

PROPOSED
-> POLICY_CHECKED
-> APPROVAL_REQUIRED or AUTHORIZED
-> CREDENTIAL_LEASED
-> EXECUTING
-> EFFECT_OBSERVED
-> VERIFYING
-> VERIFIED | PARTIAL | UNKNOWN | FAILED
-> COMMITTED | COMPENSATING | RECONCILING

UNKNOWN is a first-class state and cannot automatically retry an externally mutating operation until reconciliation proves it safe.

## Authorization rule

Frontend UI state is never authority. Backend Trust/Governance validates:

1. actor identity
2. tenant/environment
3. capability grant
4. policy version/hash
5. approval validity and expiry
6. risk ceiling
7. credential lease scope
8. idempotency constraints
9. release/environment policy

Any missing element fails closed.

## Credential rule

Execution receives a scoped lease/reference from Credential Broker. Raw secrets must not be embedded in:
- prompts
- events
- evidence
- logs
- manifests
- browser state

## Idempotency rule

Every side effect declares its idempotency semantics:
- provider_native
- ck_durable_key
- non_idempotent_reconcile_required

For `non_idempotent_reconcile_required`, timeout/network ambiguity produces UNKNOWN and blocks retry until target state is checked.

## Verification rule

A successful transport response is not equivalent to business success. Verification may include:
- read-after-write
- contract/schema validation
- target state comparison
- checksum/hash verification
- independent provider query
- policy invariant checks

## Compensation rule

Compensation is explicit and never assumed to be rollback-equivalent. Each capability declares:
- reversible: true/false/partial
- compensation capability id
- compensation preconditions
- irreversible fields

High-impact irreversible actions require explicit approval policy.

## Evidence minimum

For every impactful action, evidence must answer:
- who/what requested it
- what capability executed it
- why policy allowed it
- what credential scope was used
- what target changed
- what verification proved
- whether result is durable/known

## Security boundary

PCE does not weaken or replace security review, sandboxing, Q10, release gates, or owner approval. It provides a verifiable execution envelope once those controls authorize an action.