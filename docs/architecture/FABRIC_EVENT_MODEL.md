# CK-NEXUS Fabric Event Model

Status: SPEC_ONLY
Version: 0.1

The Event Fabric is the decoupling backbone for CK-NEXUS. Events communicate facts and requests, but MUST NOT be treated as authorization grants.

## Event envelope

Every event SHOULD include:
- `event_id`: immutable globally unique ID
- `event_type`: namespaced semantic event name
- `event_version`: event schema version
- `occurred_at`: producer timestamp
- `recorded_at`: Event Fabric timestamp
- `producer`: manifest/component identity
- `tenant_id`
- `principal_id` when relevant
- `session_id` when relevant
- `execution_id` when relevant
- `correlation_id`
- `causation_id`
- `trace_id`
- `ordering_key` when ordering matters
- `idempotency_key` when duplicate handling matters
- `data_classification`
- `payload_schema`
- `payload`
- `evidence_refs`
- `policy_context_ref` for consequential events

## Event classes

### Facts
Examples:
- `github.issue.created`
- `credential.lease.expired`
- `provider.health.degraded`
- `ck.execution.completed`

Facts describe something that occurred. They are immutable.

### Requests
Examples:
- `ck.task.assigned`
- `ck.workflow.requested`
- `ck.capability.probe.requested`

A request event is not a command with implicit authority. The consumer must authorize the requested action.

### Decisions
Examples:
- `ck.policy.allowed`
- `ck.policy.denied`
- `ck.approval.granted`
- `ck.release_gate.blocked`

Decision events reference the policy/ruleset version and evidence used to reach the decision.

## Delivery semantics

Default assumption is at-least-once delivery. Therefore consumers MUST be duplicate-safe.

For side effects:
1. consume event
2. validate schema
3. check deduplication/idempotency state
4. resolve current policy
5. obtain/validate capability grant
6. execute guarded side effect
7. verify postcondition
8. persist receipt/evidence
9. commit consumer offset/state

Never perform an external mutation before durable idempotency state is available when duplicate execution could cause harm.

## Replay

Replay is allowed only when:
- event schema version is still supported or migratable
- workflow/capability versions are pinned or intentionally re-resolved
- replay policy allows side effects
- consequential consumers enter `DRY_RUN`, `VERIFY_ONLY`, or an explicitly authorized replay mode unless re-execution is intended

Historical event replay MUST NOT automatically repeat external mutations.

## Dead-letter handling

Events enter dead-letter state when failures are not safely retryable, including:
- invalid schema
- missing required manifest version
- denied policy
- permanent auth failure
- incompatible contract
- exhausted retry budget
- unsupported data classification

Dead-letter records preserve original envelope, error classification, attempt history, and evidence references.

## Retry classes

- `TRANSIENT_NETWORK`: exponential backoff + jitter
- `RATE_LIMIT`: provider-directed retry-after + quota policy
- `AUTH_REFRESHABLE`: refresh authorized lease, then retry
- `AUTH_OWNER_ACTION_REQUIRED`: stop and request owner action
- `POLICY_DENIED`: no retry until policy context changes
- `CONTRACT_INVALID`: no blind retry
- `DEPENDENCY_UNAVAILABLE`: alternate capability/failover when policy permits
- `SIDE_EFFECT_UNCERTAIN`: verify external postcondition before any retry
- `PERMANENT`: dead-letter

## Event naming

Recommended convention:
`<domain>.<entity>.<verb>`

Examples:
- `ck.capability.registered`
- `ck.workflow.started`
- `ck.workflow.compensated`
- `ck.evidence.accepted`
- `ck.evidence.rejected`
- `ck.security.finding.validated`

## Security properties

- Events are untrusted input at every consumer boundary.
- Producer identity should be attestable where possible.
- Sensitive payloads should use references/tokenized handles rather than raw credentials or unnecessary personal data.
- Raw API keys, OAuth refresh tokens, session secrets, and private signing material MUST NOT appear in event payloads.
- Event visibility is tenant and classification scoped.

## Observability

Each event hop should emit trace linkage using correlation/causation/trace IDs. Operational dashboards may derive workflow latency, retry rate, dead-letter rate, and capability health from Event Fabric telemetry without making observability storage the source of execution authority.