# AGNES Capability Map

## Purpose

This document maps AGNES into four practical views:

1. tools and runtime surfaces
2. skill inventory
3. concept and architecture model
4. capability, risk, and approval boundaries

AGNES is a governed capability layer, not a source of truth by itself. It must
operate through runtime, policy, verification, and evidence.

## Runtime Surfaces

| Surface | Purpose | Risk | Approval | Evidence |
|---|---|---:|---|---|
| `AgnesNervousSystem.status()` | Snapshot of policy, inference, ledger, execution kernel, and discovery state | read-only | no | ledger verify + kernel status |
| `AgnesNervousSystem.skills()` | List canonical skills from the manifest | read-only | no | manifest load/validation |
| `AgnesNervousSystem.plan(goal)` | Select skill candidates for a goal | read-only | no | plan record |
| `AgnesNervousSystem.authorize_skill(...)` | Enforce API-key, production, and approval policy | policy gate | yes for protected actions | policy exception / approval state |
| `AgnesNervousSystem.record_learning(...)` | Append verified knowledge with supersession links | local write | no | append-only ledger |
| `AgnesNervousSystem.execute_skill(...)` | Build execution request and dispatch it | depends on skill | sometimes | execution result + ledger evidence |
| `AgnesNervousSystem.discovery_sources()` | List trusted discovery sources | read-only | no | discovery catalog |
| `AgnesNervousSystem.model_watch_plan()` | Plan model discovery / verification pipeline | read-only | no | watch plan output |
| `AgnesNervousSystem.self_upgrade_plan()` | Describe governed self-upgrade lifecycle | high impact | yes for execution | upgrade plan output |
| `/api/agnes/status` | Redacted public AGNES status | read-only | no | status payload |
| `/api/agnes/skills` | Public skill list | read-only | no | manifest-backed list |
| `/api/agnes/plan` | Goal-to-skill planner | read-only | no | plan payload |
| `/api/agnes/upgrade-plan` | Self-upgrade plan generator | read-only | no | plan payload |
| `/api/agnes/execute` | Execute a governed skill request | policy-bound | sometimes | execution result |
| `/api/agnes/pipeline/start` | Start autonomous dev pipeline | high impact | yes | pipeline state |
| `/api/agnes/pipeline/{id}/advance` | Advance pipeline to candidate | high impact | yes | candidate artifact |
| `/api/agnes/pipeline/{id}` | Read pipeline state or candidate | read-only | no | pipeline status |
| `/api/agnes/pipeline/{id}/discard` | Discard a candidate pipeline | destructive-ish | yes | discard state |
| `/api/agnes/approvals` | Register sticky approvals | policy gate | yes | approval record |

## Skill Catalog

The canonical skill manifest lives in `creator_app/skills/agnes/SKILL.md`.

| Skill | Organ | Purpose | Risk | Approval | Executor |
|---|---|---|---|---|---|
| `brain.plan` | brain | Break a goal into bounded, auditable steps | read_only | no | internal |
| `brain.verify_sources` | brain | Cross-check claims against trusted and primary sources | read_only | no | research |
| `eyes.web_research` | eyes | Read public web sources through an approved connector | read_only | no | mcp_or_hosted |
| `eyes.model_watch_50` | eyes | Discover and deduplicate up to 50 newly listed AI models | read_only | no | research |
| `eyes.file_read` | eyes | Read approved project files without mutation | read_only | no | workspace |
| `eyes.image_understand` | eyes | Extract structured observations from images | read_only | no | provider |
| `ears.transcribe` | ears | Transcribe approved audio through a brokered adapter | read_only | no | provider |
| `memory.append_knowledge` | memory | Append verified knowledge with provenance and supersession links | local_write | no | ledger |
| `nerves.trace` | nervous_system | Record correlated execution, tool, approval, and evidence events | local_write | no | ledger |
| `immune.policy_check` | immune_system | Evaluate tool, credential, network, approval, and environment policy | read_only | no | internal |
| `immune.skill_quarantine` | immune_system | Quarantine newly discovered skills until reviewed | local_write | no | internal |
| `hands.code_patch` | hands | Apply a bounded patch inside an isolated workspace | local_write | no | sandbox |
| `hands.test` | hands | Run compile/unit/integration checks in isolation | local_write | no | sandbox |
| `hands.security_scan` | hands | Run secret, dependency, SAST, and policy scans | local_write | no | sandbox |
| `legs.workspace_open` | legs | Create or select an isolated workspace through the broker | external_write | yes | workspace_broker |
| `legs.git_branch` | legs | Create a feature branch without rewriting history | local_write | no | workspace |
| `mouth.report` | mouth | Produce a concise evidence-backed report | read_only | no | provider |
| `upgrade.self_improve` | nervous_system | Run the governed self-upgrade lifecycle | high_impact | yes | controller |

## Capability Groups

### Read-only capabilities

- source verification
- web research
- file reading
- image understanding
- transcription
- reporting
- planning
- discovery catalog lookup

These are safe to expose broadly because they do not mutate durable state.

### Local write capabilities

- append knowledge
- trace/audit
- quarantine skills
- patch code
- run tests
- run security scans
- create branches

These mutate local or governed evidence state, but remain bounded and auditable.

### High-impact capabilities

- open external workspaces
- self-upgrade orchestration

These require explicit approval because they can expand scope, write externally,
or change the operational boundary.

## Concept Map

AGNES follows a strict separation of concerns:

- `Brain` decides and routes.
- `Eyes` observe current, public, and project context.
- `Ears` ingest audio and event streams.
- `Hands` perform bounded implementation and verification work.
- `Legs` move work into brokered workspaces.
- `Mouth` explains and reports.
- `Memory` stores append-only knowledge and evidence.
- `Nervous system` coordinates events, traces, approvals, and transitions.
- `Immune system` blocks unsafe, unaudited, or policy-breaking actions.

## Architecture Alignment

AGNES fits the unified runtime blueprint as follows:

- Experience plane: UI and API status surfaces
- Control plane: registries, policy, approvals, identity, event bus
- Cognitive plane: planning, routing, critic, risk, memory
- Integration fabric: MCP, OAuth, REST, GitHub, Drive, Slack, databases
- Execution plane: dispatcher, sandbox, connector/provider execution
- Verification plane: result, side-effect, and security verification
- Evidence fabric: ledger, provenance, attestation, release gates

## Hard Rules

- AGNES never receives raw user API keys.
- AGNES does not own permission.
- AGNES does not bypass the executor.
- UI never becomes authority.
- Model never becomes source of truth.
- No evidence means no pass.
- Approval is sticky to the exact execution fingerprint.
- Production mutation remains approval-gated.

## Practical Use

Use this map when you need to:

- decide which AGNES skill fits a task
- understand what needs approval
- explain why a result is or is not trustworthy
- find the runtime surface that exposes a capability
- separate read-only, local-write, and high-impact actions

