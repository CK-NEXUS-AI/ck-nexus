# Telemetry and Event Correlation

Status: architecture contract.

## Correlation model

A user goal receives a `correlation_id` and task ID. Downstream planning, capability decisions, approvals, AGNES nodes, execution attempts, connector/provider requests, reconciliation, verification, incidents and evidence propagate correlation references.

## Identifiers

- correlation_id: end-to-end user/business operation;
- task_id: AGNES durable task;
- node_id: DAG node;
- attempt_id: immutable execution attempt;
- command_id: Control Plane mutation request;
- approval_id: scoped approval;
- decision_id: capability selection;
- operation_id: durable action journal operation;
- receipt_id: execution receipt;
- incident_id: incident group;
- evidence_id/ref: immutable evidence artifact.

Provider request IDs are retained only when safe and useful, and never replace CK identifiers.

## Trace boundaries

Remote provider/connector calls create client spans with semantic implementation/capability labels and redacted target type. External side effects additionally link durable journal operation and execution receipt.

## Event causality

Event envelopes distinguish causation ID from correlation ID. Replayed events preserve original event identity; consumer attempts have separate attempt IDs so replay does not impersonate a new business action.

## Clock and ordering

Distributed timestamps are observations, not a total order. Durable state versions/sequence numbers provide ordering where required. Evidence records include producer time and collection time when clocks may differ.

## Redaction

Logs/traces/events use centralized redaction profiles. Secret material is represented only by opaque references/fingerprints. User/customer content is minimized and classified.
