# CK-NEXUS Two-Chat Development Coordination

Status: Development coordination only. No release or production authority.

## Shared source of truth

- Repository: `spinlnw10-art/ck-nexus`
- Coordination branch: `post-p0/two-chat-coordination-v1`
- Parent UI subject: `7c941616fb592947eb46b4d080f63369b5ff3d39`
- Production closure remains independent and unchanged.

## Chat A — Core / Runtime / Backend

Owns:
- Cognitive Event Bus contracts
- State Projector
- AGNES runtime event mapping
- read-only runtime APIs for UI
- Evidence / verifier projection contracts
- event identity, correlation, causation and digests
- tests for deterministic truth-state projection

Must not:
- change visual assets or animation implementation
- merge/deploy production
- invent UI state not represented by runtime contracts

## Chat B — UI / 3D / Windows Runtime

Owns:
- Thai-first Cognitive Digital Twin UI
- Three.js / VRM renderer integration
- avatar motion, gaze, viseme and gesture presentation
- Agent Inspector and visual operational language
- LOD, accessibility and performance governor
- Windows development host and preview runtime

Must not:
- create a second source of truth for runtime state
- grant authority to avatars
- expose private chain-of-thought or raw credentials
- merge/deploy production

## Shared contract

Both chats use the same lifecycle:

`TASK -> EXACT SUBJECT -> IMPLEMENT -> TEST -> VERIFY -> EVIDENCE -> HANDOFF`

A handoff is valid only when it records:
- exact commit SHA
- changed files
- public contracts changed
- tests executed
- CI/security result
- known blockers
- next owner

## Conflict prevention

1. Chat A owns backend/runtime contract files.
2. Chat B owns UI/renderer/assets and Windows preview scripts.
3. Shared files require an explicit handoff first.
4. Never overwrite another chat's unverified commit.
5. Rebase/retarget only after recording the previous exact SHA.
6. Development PASS never implies Release PASS or Production Ready.

## Visual truth rule

The Digital Twin may show only:
- OBSERVED: directly returned by runtime/event data
- INFERRED: derived presentation state and explicitly labelled
- SIMULATED: sandbox/what-if state and explicitly labelled
- VERIFIED: backed by verifier/evidence

Private model chain-of-thought is never rendered.

## Handoff template

```text
CHAT: A | B
STATUS: IMPLEMENTED | TESTING | PASS | BLOCKED
SUBJECT: <exact SHA>
FILES: <paths>
CONTRACTS: <changed interfaces/events>
TESTS: <commands/workflows + result>
SECURITY: <result>
BLOCKERS: <none or explicit list>
NEXT_OWNER: A | B
NEXT_ACTION: <single concrete action>
```
