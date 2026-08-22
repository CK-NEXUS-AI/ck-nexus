# CK-NEXUS Inter-Chat Communication Bus v1.1

Status: development coordination only. No release or production authority.

## Purpose

Provide a durable, auditable communication and work-dispatch layer that any authorized CK-NEXUS development chat/agent can use to publish, receive, claim, acknowledge, execute, and hand off bounded development work without relying on hidden chat memory.

## Authority boundary

- CK-NEXUS remains authority for state, policy, permissions, execution, and evidence.
- A chat/agent message is advisory until accepted by the owning workflow and verified against evidence.
- No chat may self-authorize merge, deploy, production mutation, credential disclosure, or release promotion.
- Private chain-of-thought, raw credentials, tokens, passwords, and secret-bearing payloads are forbidden.
- ACK, CLAIM, and COMPLETE are coordination states; none of them is release approval.

## Transport

The durable transport for v1.1 is the canonical GitHub repository coordination surface. Issue #141 is the live shared stream. Machine-readable envelopes follow the schema below.

## Message envelope v1.1

```json
{
  "schema": "cknexus.inter_chat.message.v1.1",
  "message_id": "msg_<uuid>",
  "channel": "coordination",
  "from": "dispatcher",
  "to": ["chat-a", "chat-b"],
  "type": "WORK_REQUEST",
  "created_at": "RFC3339 timestamp",
  "correlation_id": "stable work id",
  "causation_id": "optional prior message id",
  "repository": "spinlnw10-art/ck-nexus",
  "subject_sha": "exact commit SHA or null",
  "truth_class": "OBSERVED",
  "priority": "P1",
  "required_capabilities": ["runtime", "python"],
  "summary": "public concise message",
  "contracts": [],
  "tests": [],
  "evidence": [],
  "blockers": [],
  "lease_seconds": 3600,
  "next_owner": "auto",
  "next_action": "single concrete action",
  "requires_ack": true
}
```

## Message types

- `ANNOUNCE`: capability/status broadcast.
- `REQUEST`: asks another owner for bounded information/action.
- `WORK_REQUEST`: dispatchable task with required capabilities.
- `CLAIM`: a participant leases one work request.
- `HEARTBEAT`: extends an active lease while work is progressing.
- `RELEASE`: voluntarily releases a claim for requeue.
- `EXPIRE`: records that a stale claim is eligible for requeue.
- `HANDOFF`: transfers ownership of a defined next action.
- `RESULT`: returns work/evidence.
- `BLOCKER`: records a fail-closed dependency.
- `COMPLETE`: marks development work complete after required verification evidence is attached.
- `ACK`: acknowledges receipt only; ACK is not approval.
- `SUPERSEDE`: explicitly replaces an earlier message while preserving history.

## Capability routing

Participants advertise stable public capabilities in the manifest. Dispatch chooses only participants whose advertised capabilities satisfy `required_capabilities`.

Examples:

- `chat-a`: runtime, backend, event-bus, state-projector, python, api
- `chat-b`: ui, browser, windows, threejs, vrm, accessibility
- `codex-security`: security-scan, finding-validation, attack-path
- `independent-verifier`: verification, evidence-review, provenance

Capability routing does not grant additional permissions.

## Claim / lease protocol

1. Dispatcher publishes `WORK_REQUEST` with `correlation_id`, capabilities and bounded scope.
2. Eligible participant publishes `CLAIM` referencing the request message id.
3. A claim is valid only for `lease_seconds` and only one active claim may own a work id.
4. Long work publishes `HEARTBEAT` before lease expiry.
5. On success, participant publishes `RESULT`, then `COMPLETE` only when required tests/evidence are present.
6. On inability to continue, publish `RELEASE` or `BLOCKER`.
7. Stale leases are recorded with `EXPIRE`; the work becomes eligible for requeue.
8. Conflicting claims are resolved deterministically by earliest accepted `created_at`; later claims become no-op acknowledgements.

## Automatic dispatch rules

The dispatcher may automatically:

- inspect unclaimed work;
- match advertised capabilities;
- publish routing requests;
- detect expired leases;
- requeue orphaned tasks;
- request missing evidence;
- request handoffs between development owners.

The dispatcher may not automatically:

- merge pull requests;
- deploy;
- mutate production;
- create or expose credentials;
- promote Q10/Q11/Q12;
- convert Development PASS into Release PASS;
- approve its own evidence.

A ChatGPT conversation that is not actively running cannot be remotely awakened by this bus. When that participant next runs, it can read Issue #141 and claim outstanding work. Persistent external workers/agents may poll the bus independently when separately authorized.

## Truth classes

- `OBSERVED`: directly read from repository/runtime/tool output.
- `INFERRED`: derived interpretation; must be labelled.
- `SIMULATED`: sandbox/what-if only.
- `VERIFIED`: backed by explicit verifier/evidence references.

A message may never upgrade itself to VERIFIED without evidence.

## Delivery semantics

1. Messages are append-only.
2. `message_id` must be globally unique.
3. Duplicate `message_id` is idempotent and ignored after the first accepted copy.
4. Ordering is reconstructed with `created_at`, `correlation_id`, and `causation_id`; consumers tolerate out-of-order delivery.
5. A required ACK confirms receipt, not correctness or approval.
6. `SUPERSEDE` never deletes the earlier message.
7. Subject-bound evidence becomes stale when its subject changes.
8. Work identity is `correlation_id`; message identity is `message_id`.

## Channels

- `coordination`: general development coordination.
- `runtime`: Core/Runtime/Backend and State Projector work.
- `ui`: UI/3D/Windows work.
- `security`: security findings and verification; no secrets.
- `release`: release evidence references only; cannot authorize release.
- `ops`: infrastructure/readiness and operational blockers.

## Acceptance gate

Reject or quarantine a message when:

- schema/version is unknown;
- `message_id` is absent or duplicated with different content;
- sender/recipient is invalid;
- a required exact `subject_sha` is absent;
- `VERIFIED` lacks evidence;
- payload contains raw credentials/private chain-of-thought;
- requested action exceeds recipient authority;
- claim references unknown work;
- lease duration exceeds policy maximum;
- production mutation is requested without the separate governed approval path.

## Production boundary

This bus cannot turn Development PASS into Release PASS. Q10/Q11/Q12, provenance, checksummed package, independent review, and governed human release decision remain separate fail-closed gates.
