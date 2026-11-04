# CK-NEXUS Cognitive Control Universe

## Status

This feature is a runtime visualization and control surface. It does **not** change CK-NEXUS production readiness. Production remains governed by the existing release gates and evidence attached to the exact source subject.

The frontend is a **projection**, never an authority. It must not invent task state, progress, tool activity, model activity, verification results, cost, CPU/GPU usage, or evidence.

## Runtime layers

1. Experience / Visualization — Chat, Live Workspace, AI Office, Graph, Console, Evidence.
2. Control Plane — access gateway, identity, tenant boundary, policy, approval and budget.
3. Cognitive Execution Plane — planner, graph, AGNES, agent runtime and model router.
4. Execution Fabric — tools, APIs, files, databases, web and integrations.
5. Verification / Evidence Plane — validation, policy result, hashes and append-only evidence.
6. Observability / Event Plane — events, metrics, logs, traces and checkpoints.

## Cognitive scale

| Scale | Layer | Intended runtime object |
| --- | --- | --- |
| 12 | SYSTEM | Runtime system |
| 11 | WORKSPACE | Tenant / workspace |
| 10 | MISSION | Mission |
| 09 | TASK | Task |
| 08 | WORKFLOW | Graph / workflow |
| 07 | COUNCIL | Agent team |
| 06 | AGENT | Agent session |
| 05 | MODEL | Model invocation |
| 04 | TOOL | Tool invocation |
| 03 | NODE | Execution node |
| 02 | VERIFY | Verification record |
| 01 | EVIDENCE | Evidence record |

Semantic zoom must change the runtime object being inspected, not merely scale a decorative canvas.

## Current implementation truth boundary

The first implementation intentionally distinguishes current backend capability from the target architecture:

- `/api/control-universe/overview` reads actual app state, provider status, database readiness, runtime binding state, AGNES policy/status and ledger verification.
- `/api/control-universe/events` projects records from the existing AGNES hash-chained JSONL ledger.
- `/api/control-universe/stream` streams newly appended ledger records over authenticated SSE.
- `/api/control-universe/evidence` exposes ledger verification and records.
- `/api/control-universe/graph` is explicitly marked `RUNTIME_CAPABILITY_PROJECTION` and `authoritative_task_graph=false`.
- pause/resume/cancel/retry commands fail closed with `CONTROL_ADAPTER_UNAVAILABLE` until an authoritative task-control adapter is connected.
- Agent cards are catalog projections; runtime state and progress remain `UNKNOWN` unless a task-scoped runtime source exists.
- CPU, GPU, token rate and cost remain `NOT_COLLECTED` when no real collector/provider usage source is wired.
- Evidence is described as hash-chained append-only data. The UI does not claim immutable storage.

## State policy

Canonical task state should converge on one state machine:

`CREATED -> PLANNING -> QUEUED -> RUNNING -> COMPLETED`

Intermediate states may include `WAITING_TOOL`, `TOOL_RUNNING`, `WAITING_DEPENDENCY`, `WAITING_APPROVAL`, `VERIFYING`, `PAUSING`, `PAUSED`, and `RETRYING`.

Terminal alternatives are `FAILED`, `BLOCKED`, `CANCELLED`, `TIMED_OUT`, and `PARTIAL`.

Each UI view must map from the same state and event source.

## Command versus event

A command is a request to change runtime state. An event confirms what actually occurred.

Example:

`task.pause command -> authorization -> governor -> runtime adapter -> task.paused event -> UI projection`

The browser may show `PAUSE REQUESTED` while waiting, but must not show `PAUSED` before the backend confirms it.

## Event contract target

A canonical event should carry, where applicable:

- schema version and monotonic sequence
- event ID and event type
- system, tenant, mission, task, run, graph, node and agent IDs
- correlation, causation, trace and span IDs
- previous and current state
- progress mode and measured units
- policy ID, decision and risk
- tool invocation identity and status
- verification ID and evidence ID
- timestamp and provenance

The existing ledger projection supplies only the fields that are supported by current records. Missing fields must remain absent or unknown.

## Visual semantics

- Cyan: active execution
- Blue: agent identity
- Violet: model activity
- Green: verified/pass
- Amber: approval/policy waiting
- Red: fail/block/stop
- Gold: evidence/provenance
- Slate: queued/inactive/unknown

Visual effects are semantic. A pulse, data packet, office-room highlight or evidence flash should be driven by a real event, not a random animation loop.

## Thai-first typography

Thai is the primary interface language. English is a technical secondary label. The preferred stack is Anuphan for display, IBM Plex Sans Thai or Noto Sans Thai for UI/body, and a monospace font only for IDs, hashes, traces and metrics. The implementation uses local/system fallbacks to preserve the existing self-only CSP and does not load remote font files.

## Security invariants

- Existing access-token protection is preserved for control-universe data endpoints.
- The HTML shell itself contains no secrets.
- No credential values are returned to the control-universe API.
- Mutations must pass authorization and policy enforcement before an execution adapter acts.
- Unsupported mutation fails closed.
- Historical replay is a projection; it must not mutate live runtime state.
- A future fork-from-checkpoint operation must be a separately authorized command.

## Next runtime integrations

The next implementation phase should bind the UI to a canonical task execution adapter that publishes task/node/model/tool state changes with sequence numbers and checkpoints. Only after that binding exists should Pause, Resume, Cancel, Retry, weighted task progress, model usage, tool latency, timeline replay and AI Office animation be promoted from `UNKNOWN`/disabled to live task-scoped capabilities.
