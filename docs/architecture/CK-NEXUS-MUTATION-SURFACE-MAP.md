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

## 7. Test / Evidence Boundary

The supplied OpenClaw testing guidance is treated as **test-method evidence**, not runtime proof of CK-NEXUS coverage.

Evidence tiers for this map:

1. **STATIC DOCUMENTED** — OpenClaw source/docs identify a capability or test lane.
2. **LOCAL EXECUTED** — a permitted, bounded local command ran successfully.
3. **REMOTE EXECUTED** — Crabbox/Testbox/CI ran the relevant test against the intended SHA.
4. **RUNTIME VERIFIED** — the result demonstrates the actual target deployment's enabled surface and governance behavior.
5. **COVERAGE VERIFIED** — the full mutation path, including leaf effects, is proven MEDIATED.
6. **PRODUCTION** — independent release gates are closed; this is not implied by any test result alone.

Important constraints from the testing guidance:

- Do not run large/heavy repository tests locally merely because a remote provider is unavailable.
- `pnpm test:changed` and targeted Vitest are bounded local evidence lanes when dependencies are available.
- `pnpm check:changed` classifies the change before selecting local versus remote execution.
- Large distributed checks, Docker, E2E, live evidence, and cross-platform checks belong in Crabbox/Testbox/CI when required by the repository workflow.
- `OPENCLAW_TESTBOX_ALLOW_STALE=1` is diagnostic only and is **not release evidence**.
- A cancelled outer GitHub Action is not by itself a test failure if the wrapper reports successful command execution; wrapper exit code and captured JSON are the authoritative result for that lane.
- Live-provider tests require explicit live credentials and are therefore **out of scope for this read-only mapping phase**.
- Docker/Plugin/browser/MCP lanes prove their respective test scenarios; they do **not** by themselves prove CK-NEXUS Gateway mediation.

Therefore:
> A test PASS establishes only the scope of the test that actually ran. It does not upgrade an unrelated mutation surface from UNKNOWN to MEDIATED.

## 8. Surface-to-Test Discovery Matrix

| Surface | Static discovery | Candidate bounded test | Coverage proof still required |
|---|---|---|---|
| S01 exec | tools/exec docs + source | targeted exec smoke | Gateway deny/allow + leaf containment |
| S02 process | process/tool source | process lifecycle smoke | lease + expiry + kill/quarantine |
| S03 browser | browser tool docs/source | browser E2E/CDP lane | submit/side-effect mediation |
| S04 MCP | MCP docs/source | MCP serve/channel lane | downstream mutation leaf |
| S05 filesystem | exec/plugin source | targeted write fixture | policy-bound filesystem enforcement |
| S06 network | sandbox/network config | network-deny fixture | network interception/egress proof |
| S07 plugin | plugin docs/source | plugin install/update Docker lane | admission + re-scan + capability boundary |
| S08 skill | SKILL.md/plugin source | targeted skill test | invoked-tool mediation |
| S09 sub-agent | delegation source | delegated-agent fixture | narrowed lease proof |
| S10 credentials | provider/auth source | redaction/config inspection only | broker enforcement without exposing secrets |
| S11 device/node | node/device source | bounded node inventory | remote authority boundary |
| S12 message/channel | channel source | mocked send path | human/approval binding |
| S13 web_search | web tool source | bounded fetch fixture | egress + data-loss controls |
| S14 scheduling | cron/task source | delayed test fixture | fire-time approval re-check |

## 9. Runtime Questions

- Which surfaces are actually enabled?
- Does exec run inside a sandbox that blocks network by default?
- Do MCP calls expose downstream mutation?
- Does plugin installation require a Gateway decision?
- Do sub-agents inherit leases, and are they narrowed?
- Is scheduling enabled, and is expiry re-checked at fire time?
- Is any native path able to bypass tool policy?

## 10. Evidence Log

| Source | Claim | Status |
|---|---|---|
| OpenClaw documentation supplied in task | testing lanes and remote/local execution policy exist | DOCUMENTED |
| Target runtime | actual enabled surfaces / policy holes | NOT COLLECTED |
| CK-NEXUS Gateway | universal mediation | NOT IMPLEMENTED / NOT VERIFIED |

## 11. Status

```
P0.2 Mutation Surface Mapping = DESIGNED
Test-method mapping             = DESIGNED
Runtime verification             = NOT STARTED
Coverage                         = UNKNOWN (14/14)
Production                       = NO-GO
```
