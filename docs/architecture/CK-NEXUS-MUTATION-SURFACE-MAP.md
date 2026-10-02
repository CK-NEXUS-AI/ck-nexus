# CK-NEXUS · Mutation Surface Map (OpenClaw)

> Status: **DESIGNED / STATIC RESEARCH**
> Runtime evidence: **NOT COLLECTED**
> Owner: CK-NEXUS Authority Layer

## 1. Purpose

Enumerate every channel through which OpenClaw (Worker) can mutate state outside the agent's own internal reasoning, so the Enforcement Gateway (P0.1) can cover all exits rather than a subset.

> If we do not know every exit, we cannot prove coverage. A Gateway that covers "most exits" is a Gateway with a bypass.

## 2. Definitions

| Term | Meaning |
|---|---|
| Mutation | Any change to state outside the agent's in-process memory. |
| Surface | A named channel through which mutation can occur. |
| MEDIATED | The mutation path passes through a CK-NEXUS Enforcement Gateway decision. |
| UNMEDIATED | The mutation path is reachable without a Gateway decision. |
| UNKNOWN | No runtime evidence yet. **Never treated as SAFE.** |

Strict status vocabulary: `DESIGNED ≠ IMPLEMENTED ≠ EXECUTED ≠ VERIFIED`.

## 3. OpenClaw capability classes (documented; runtime confirmation outstanding)

- `exec` — shell / Python / Node / git / arbitrary CLI
- `process` — long-running / background jobs
- `browser` — click / submit / download / DOM
- `web_search` — outbound fetch; potentially exfil-capable
- `message` / channel — send / post / action
- `plugins` — add tools, skills, providers, channels, runtime
- `skills` — SKILL.md instruction packages that may invoke tools
- MCP — Model Context Protocol server calls
- providers — model/provider surfaces
- sub-agent / delegation
- device/node — external machine execution
- scheduling — deferred / recurring automation if enabled

## 4. Surface Registry

| # | Surface | Primitive | Example mutation | Risk | Coverage |
|---|---|---|---|---|---|
| S01 | exec | `exec` | shell / Python / Node / git write | high | UNKNOWN |
| S02 | process | `process` | background / long-running job | high | UNKNOWN |
| S03 | browser | `browser` | click / submit / download | high | UNKNOWN |
| S04 | MCP | MCP server | external tool/server call | high | UNKNOWN |
| S05 | filesystem | exec / plugin | write / delete / move | high | UNKNOWN |
| S06 | network | exec / browser / fetch | HTTP / API / socket | high | UNKNOWN |
| S07 | plugin | plugins | install capability / invoke tool | high | UNKNOWN |
| S08 | skill | skills | workflow invoking tools | medium | UNKNOWN |
| S09 | sub-agent | delegation | delegated agent action | high | UNKNOWN |
| S10 | credentials | broker / env | secret / API-key access | critical | UNKNOWN |
| S11 | device/node | remote node | external machine execution | high | UNKNOWN |
| S12 | message/channel | message | send / post / action | medium | UNKNOWN |
| S13 | web_search | web_search | outbound fetch / possible exfil | medium | UNKNOWN |
| S14 | scheduling | automation | deferred / recurring mutation | high | UNKNOWN |

S13 and S14 are included because outbound fetch and deferred execution can create governance bypasses.

## 5. Composite / Bypass Paths

### C1 — exec → network
```
Agent → Gateway(ALLOW exec) → script → direct network call
exec: MEDIATED
network: UNMEDIATED
coverage: INCOMPLETE
```

### C2 — MCP → external API mutation
```
Agent → Gateway(ALLOW MCP) → MCP server → external API mutation
MCP: MEDIATED
API mutation: UNKNOWN
coverage: INCOMPLETE
```

### C3 — plugin install → new surface
```
Agent → install plugin → plugin adds new tool/network channel
plugin entry: possibly mediated
new surface: UNKNOWN
coverage: INCOMPLETE
```

### C4 — sub-agent authority inheritance
```
Agent(lease L) → spawn sub-agent → sub-agent acts with/without L
If authority is not inherited-and-narrowed, authority may escape scope.
coverage: INCOMPLETE
```

### C5 — scheduling → deferred decision
```
Agent → ALLOW(schedule job) → later job mutates
approval may expire before fire time
coverage: INCOMPLETE unless validity is re-checked at fire time
```

## 6. Coverage Invariant

For every mutation M:

```
agent_id → lease_id → policy_version → approval_id
        → mutation_surface → resource
        → gateway_decision → execution → post_receipt
```

Missing any link is a coverage gap.

## 7. Runtime Questions

- Which surfaces are actually enabled?
- Does exec run inside a sandbox that blocks network by default?
- Do MCP calls expose downstream mutation?
- Does plugin installation require a Gateway decision?
- Do sub-agents inherit leases, and are they narrowed?
- Is scheduling enabled, and is expiry re-checked at fire time?
- Is any native path able to bypass tool policy?

## 8. Evidence Log

| Source | Claim | Status |
|---|---|---|
| OpenClaw documentation | capability classes exist | DOCUMENTED |
| Target runtime | actual enabled surfaces / policy holes | NOT COLLECTED |

## 9. Status

```
P0.2 Mutation Surface Mapping = DESIGNED
Runtime verification           = NOT STARTED
Coverage                       = UNKNOWN (14/14)
Production                     = NO-GO
```
