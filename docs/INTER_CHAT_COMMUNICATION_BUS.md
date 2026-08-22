# CK-NEXUS Inter-Chat Communication Bus v1

Status: development coordination only. No release or production authority.

## Purpose

Provide a durable, auditable communication layer that any authorized CK-NEXUS development chat/agent can use to publish, receive, acknowledge, and hand off work without relying on hidden chat memory.

## Authority boundary

- CK-NEXUS remains authority for state, policy, permissions, execution, and evidence.
- A chat/agent message is advisory until accepted by the owning workflow and verified against evidence.
- No chat may self-authorize merge, deploy, production mutation, credential disclosure, or release promotion.
- Private chain-of-thought, raw credentials, tokens, passwords, and secret-bearing payloads are forbidden.

## Transport

The durable transport for v1 is the canonical GitHub repository coordination surface. A shared issue may be used as the live conversation stream; machine-readable envelopes must follow the schema below.

## Message envelope v1

```json
{
  "schema": "cknexus.inter_chat.message.v1",
  "message_id": "msg_<uuid>",
  "channel": "coordination",
  "from": "chat-a",
  "to": ["chat-b"],
  "type": "HANDOFF",
  "created_at": "RFC3339 timestamp",
  "correlation_id": "optional stable id",
  "causation_id": "optional prior message id",
  "repository": "spinlnw10-art/ck-nexus",
  "subject_sha": "exact commit SHA or null",
  "truth_class": "OBSERVED",
  "priority": "P1",
  "summary": "public concise message",
  "contracts": [],
  "tests": [],
  "evidence": [],
  "blockers": [],
  "next_owner": "chat-b",
  "next_action": "single concrete action",
  "requires_ack": true
}
```

## Message types

- `ANNOUNCE`: capability/status broadcast.
- `REQUEST`: asks another owner for a bounded action or information.
- `HANDOFF`: transfers ownership of a defined next action.
- `RESULT`: returns verified work/evidence.
- `BLOCKER`: records a fail-closed dependency.
- `ACK`: acknowledges receipt only; ACK is not approval.
- `SUPERSEDE`: explicitly replaces an earlier message while preserving history.

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
4. Ordering must be reconstructed with `created_at`, `correlation_id`, and `causation_id`; consumers must tolerate out-of-order delivery.
5. A required ACK confirms receipt, not correctness or approval.
6. `SUPERSEDE` never deletes the earlier message.
7. Subject-bound evidence becomes stale when its subject changes.

## Channels

- `coordination`: general development coordination.
- `runtime`: Core/Runtime/Backend and State Projector work.
- `ui`: UI/3D/Windows work.
- `security`: security findings and verification; no secrets.
- `release`: release evidence references only; cannot authorize release.
- `ops`: infrastructure/readiness and operational blockers.

Additional channels may be registered in the manifest, but may not weaken governance.

## Identity

Each participant uses a stable public ID, for example:

- `chat-a`
- `chat-b`
- `chat-c`
- `codex-security`
- `independent-verifier`
- `human-owner`

The ID describes the sender role; it does not grant permissions.

## Acceptance gate

A consumer must reject or quarantine a message when:

- schema/version is unknown;
- `message_id` is absent or duplicated with different content;
- sender/recipient is invalid;
- a required exact `subject_sha` is absent;
- `VERIFIED` lacks evidence;
- payload contains raw credentials/private chain-of-thought;
- requested action exceeds recipient authority;
- production mutation is requested without the separate governed approval path.

## Handoff minimum

A valid development handoff carries:

- exact subject SHA;
- changed files or affected contracts;
- tests/workflow run IDs and results;
- security result when relevant;
- blockers;
- next owner;
- one concrete next action.

## Production boundary

This bus cannot turn Development PASS into Release PASS. Q10/Q11/Q12, provenance, checksummed package, independent review, and governed human release decision remain separate fail-closed gates.
