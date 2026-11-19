# CK-NEXUS Market Intelligence: AI Company OS & 1 Human + AI Workforce

- Research date: 2026-11-19
- Repository baseline: `117cef2423ccd9ad5791cd52075946b02cd4a680`
- Working branch: `research/ai-company-os-intel-20261119`
- Scope: read-only market research and repository capability mapping. No code deletion, dependency installation, production changes, external posting, or credentials access.
- Evidence rule: project feature descriptions below are vendor/project claims until independently validated by source review and local tests.

## Executive finding

CK-NEXUS already contains substantial building blocks for a governed AI workforce. The main opportunity is not to add another generic multi-agent framework. It is to connect existing capabilities into one auditable company operating model:

1. Organization and role directory (human owner, AI role, provider/runtime, allowed capabilities).
2. Goal-to-task planning and durable task ownership.
3. Policy decision and human approval before high-impact actions.
4. Cost/usage budgets and per-agent accounting.
5. Evidence-backed review, outcome metrics, and stop controls.
6. Market/idea intake feeding the existing proposal-only Idea Engine.

The repository inspection found existing implementations or candidate implementations for agent roles/team coordination, task queue/checkpoints, approval grants, kill switches, sandbox policy, proposal-only idea scoring, research lineage, and tests. Their presence does not prove production readiness or that all paths are wired into the canonical runtime.

## Local repository evidence observed

| Capability | Existing path | Initial assessment |
|---|---|---|
| Agent role model | `creator_app/ai_team/agent_models.py` | Roles include director, engineer, guardian, analyst, researcher, designer, connector. |
| Team coordination | `creator_app/ai_team/team_director.py` | Planner/director delegates work to specialist agents; inspect persistence and execution boundaries before reuse. |
| Durable task queue | `creator_app/control_plane/task_store.py` | SQLite queue has states, leases, attempts and checkpoints. |
| Human approval | `creator_app/agnes/execution/approval.py` | Approval grant binds to a fingerprint of execution facts and has a TTL; in-memory resolver is not durable approval storage. |
| Emergency stop | `creator_app/agnes/execution/kill_switch.py` | Global, tenant, executor and skill stop controls exist as a model. Verify enforcement wiring and persistence. |
| Sandbox | `creator_app/agnes/execution/sandbox/policy.py` | Resource limits and network-deny policy are defined. Actual kernel enforcement must be verified separately. |
| Idea intake/scoring | `idea_engine/engine.py`, `idea_engine/scoring.py` | Proposal-only engine; blocks deployment, external send, billing mutation and approval/release-gate mutation. |
| Research lineage | `idea_engine/research_repository.py` | Source/claim lineage, citations, contradiction and truth-state records exist. |
| Tests | `tests/test_control_plane_*.py`, `tests/test_universal_command_protocol.py`, `tests/test_omni_*.py`, `tests/test_r11_idea_engine_canonical.py` | Candidate test suites exist; test execution and coverage are not yet verified in this research pass. |

### Important gaps to verify before implementation

- Whether the team director's in-memory request history is superseded by the durable task store in the canonical execution path.
- Whether agent identities, role permissions and tool grants are persisted and tenant-scoped.
- Whether per-agent and per-task cost budgets exist, are enforced before model/tool calls, and reconcile estimated vs actual spend.
- Whether approval records are durable, revocable, one-time or idempotent, and bound to exact action payloads.
- Whether kill-switch state is persisted and enforced at every execution boundary.
- Whether outcome-based performance reviews exist (quality, verified completion, rework, cost, latency, policy violations), not merely task counts.
- Whether organization charts and manager/reporting relationships are represented as governed data rather than prompts.
- Whether social/market inputs can be ingested with source permissions, privacy filtering, retention limits and provenance.

## External project comparison

| Project | What it contributes | License / hosting claim | CK-NEXUS disposition |
|---|---|---|---|
| Paperclip | Company-level control plane: org chart, goals, tasks, agent roles, budgets, approvals, run history; supports multiple agent runtimes. | Project describes itself as MIT and self-hosted. Latest release page observed: v2026.1106.0. | **ADAPT ideas**: org/agent directory, budget ledger, review gates, run observability. Do not replace CK-NEXUS policy/evidence kernel. |
| OneManCompany | One-person company model with AI departments, hierarchy, delegation, quality gates, reviews and project cost tracking. | Project page states Apache-2.0 and open source. | **ADAPT ideas**: 1-human operating model, AI employee lifecycle, task quality gates, performance review. |
| Agent Swarm | One lead agent, worker agents, shared memory, deterministic steps and human approvals. | Project page states MIT and self-hosted. | **ADAPT ideas**: lead/worker routing and shared context; validate isolation, audit and permission boundaries. |
| Markus | Self-hosted AI workforce with agent roles, teams, manager, shared task board and human approval gates. | Project FAQ says software is free/self-hosted; model provider usage remains separately chargeable. | **RESEARCH**: compare team lifecycle and runtime integration; no install yet. |
| Conductor OSS | Durable event-driven workflow engine for applications and AI agents; workers can be implemented in multiple languages. | Project references Apache-2.0 and self-hosting. | **REUSE selectively** only if CK-NEXUS durability/retry requirements cannot be met by current task store; JVM/queue/persistence operations add complexity. |
| Goose | Local-first general-purpose agent with desktop, CLI, API and MCP extensions. | Project page states Apache-2.0 and AAIF affiliation. | **ADAPT connector/runtime patterns**; do not grant broad local tool access by default. |

## 1 Human + AI Workforce: proposed CK-NEXUS model

- Human owner / CEO: defines goals, approves risk-bearing actions, owns accountability.
- AI Director: decomposes goals, assigns work, monitors dependencies; cannot grant itself new permissions.
- AI Researcher / Market Analyst: gathers public and authorized sources, stores citations and provenance.
- AI Product / Engineer: creates proposals and code changes in isolated workspaces.
- AI Guardian / Auditor: independently checks policy, tests, evidence and risk; cannot approve its own work.
- AI Operations: monitors queues, budgets, service health and incident stop controls.
- AI Customer / Growth roles: draft only by default; publishing, messaging, spending and customer-data export require explicit authorization.

## Proposed integration sequence

1. **Inventory and reuse (now):** map current runtime entrypoints and existing implementations; no duplicate modules.
2. **Organization Registry (design):** define tenant-scoped human/agent identities, roles, manager links, runtime/provider references, skill/tool grants and status.
3. **Workforce Task Contract (design):** goal, task owner, reviewer, dependencies, risk class, budget ceiling, due date, required evidence and terminal state.
4. **Budget & Outcome Ledger (design):** per-agent/per-task usage receipts, hard spend limits, stop-on-exhaust, estimated/unpriced labels, and quality/rework metrics.
5. **Approval and Stop Enforcement (verify then improve):** connect existing approval and kill-switch primitives to every side-effecting execution path.
6. **Market Intelligence Intake (build only after connector permissions):** normalize public/authorized sources into research lineage, deduplicate, classify, score, and produce proposals.
7. **Sandbox validation:** tests, policy checks, license review, dependency scan, rollback plan and independent review before merge/deploy.

## Safety and acceptance rules

- Default is read-only and proposal-only.
- Never import another project's code or dependencies before checking the exact repository, license file, transitive dependencies, security posture, maintenance and overlap.
- Never delete a module because it appears unused; require import/runtime/workflow tracing and tests proving safe removal.
- Never allow an agent to approve its own high-impact action.
- No public social posting, messaging, financial transactions, campaign changes, deployment, permission changes or credential export without a separate explicit authorization.
- A passing unit test is not proof of production readiness.
- No production claim until canonical runtime wiring, independent review, security gates, operational recovery and deployment evidence are verified.

## Market research query set

Use the user's 50 Thai/English phrases under five dimensions: company operating model; governance and human control; AI job roles; operations and metrics; market comparison. Add these discovery terms for higher-precision searches:

- agentic company operating system
- AI workforce management control plane
- agent org chart and identity registry
- human approval gates for autonomous agents
- per-agent budget and cost ledger
- durable task ownership and audit trail
- least-privilege agent tool authorization
- AI employee performance evaluation
- multi-agent shared memory with tenant isolation
- self-hosted business process orchestration
- agent runtime sandbox and emergency stop
- outcome-based AI workforce metrics

## Source register

- Paperclip repository and release notes: https://github.com/paperclipai/paperclip and https://github.com/paperclipai/paperclip/releases
- OneManCompany project page and repository: https://1mancompany.github.io/OneManCompany/ and https://github.com/1mancompany/OneManCompany
- Agent Swarm project page: https://www.agent-swarm.dev/
- Markus project page: https://www.markus.global/
- Conductor OSS FAQ: https://github.com/conductor-oss/conductor/blob/main/docs/devguide/faq.md
- Goose project page and repository: https://block.github.io/goose/ and https://github.com/aaif-goose/goose

## Current disposition

- REUSE: existing CK-NEXUS modules only after runtime-path verification.
- ADAPT: Paperclip/OneManCompany/Agent Swarm organizational and workforce concepts.
- BUILD: a thin integration layer connecting organization registry, task contract, budget ledger and existing evidence/approval primitives, only after confirming missing functionality.
- REPLACE: none approved.
- REJECT: none at this stage; no project has been approved for code import.
- NOT VERIFIED: full test execution, canonical runtime wiring, durable budget enforcement, production security and deployment.
