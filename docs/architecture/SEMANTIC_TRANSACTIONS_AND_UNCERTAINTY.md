# Semantic Transactions and Uncertainty Ledger

Status: SPEC_ONLY

Traditional database transactions do not cover workflows spanning AI reasoning, external APIs, queues, human approvals, and irreversible side effects. CK-NEXUS therefore models a higher-level SemanticTransaction.

## SemanticTransaction

A SemanticTransaction groups a user intent and all derived operations that together represent one meaningful business outcome.

Fields:
- semantic_tx_id
- intent_id
- goal
- actor/tenant/environment
- task DAG version/hash
- policy snapshot
- capability bindings
- expected invariants
- declared side effects
- compensation plan
- evidence requirements
- terminal success criteria

A semantic transaction may contain multiple technical transactions while preserving one coherent audit/evidence boundary.

## Commit model

Possible terminal states:
- COMMITTED_VERIFIED
- COMMITTED_WITH_WARNINGS
- PARTIALLY_COMMITTED
- COMPENSATED
- FAILED_NO_SIDE_EFFECT
- FAILED_WITH_SIDE_EFFECT
- UNKNOWN_PENDING_RECONCILIATION
- ABORTED_BY_POLICY
- ABORTED_BY_OWNER

Only `COMMITTED_VERIFIED` is treated as fully successful by default.

## Uncertainty Ledger

The Uncertainty Ledger records facts the platform cannot yet prove.

Each entry contains:
- uncertainty_id
- semantic_tx_id/execution_id
- claim
- uncertainty class
- confidence level
- reason
- affected resources
- potential impact
- required reconciliation capability
- next check time
- evidence references
- resolution status

Classes include:
- delivery_unknown
- external_state_unknown
- stale_read
- partial_response
- duplicated_effect_possible
- identity_ambiguity
- semantic_ambiguity
- policy_version_mismatch
- evidence_gap

## Rules

1. Uncertainty must never be silently converted to success.
2. Unknown external side effects block unsafe retries.
3. High-risk unresolved uncertainty must surface in Command Center and incident workflows.
4. Reconciliation produces new evidence and resolves, narrows, or escalates an uncertainty entry.
5. Learning systems cannot train trusted routing scores from unresolved outcomes.

## Durable Action Journal

Every attempted external action is written to a durable journal before/after execution as appropriate:
- intent
- execution packet hash
- action target
- idempotency key
- attempt number
- adapter/provider
- timestamps
- observed result
- uncertainty references
- receipt/evidence references

Journal records are append-only and support crash recovery and reconciliation.

## Reconciliation loop

Observe
-> detect incomplete/unknown outcome
-> load durable journal
-> inspect target state through read-only capability
-> compare expected vs observed state
-> classify
-> verify or compensate if policy allows
-> append evidence
-> resolve uncertainty
-> emit reconciliation event

## Human interaction

When automated reconciliation cannot establish a safe state, the platform generates an operator packet containing:
- what was intended
- what is known
- what is unknown
- possible duplicate/irreversible impact
- safe options
- recommended next action

The operator is never asked to approve an action without this context when the prior outcome is uncertain.

## Relationship to Event Fabric

Events are notifications of state/evidence changes; they are not themselves the source of truth for semantic transaction completion. Completion is derived from durable journal + verification evidence + policy state.

## Relationship to Learning

Only resolved, provenance-backed outcomes may update reliability, cost, success-rate, or routing metrics. Unknown/partial outcomes are retained separately to avoid teaching the system false confidence.