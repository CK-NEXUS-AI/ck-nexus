# CK-NEXUS

**Governed Autonomous AI Operating System** — an enterprise-oriented, self-hosted platform for governed AI orchestration, controlled tool execution, persistent knowledge, and evidence-based operations.

**One Core. One Authority. Many Intelligent Agents.**

CK-NEXUS is one platform with one canonical application runtime. **Agnes** is its AI orchestration and execution layer; the Creator Workspace is a user-facing workspace; and **/development** is an internal evidence dashboard. These are parts and interfaces of CK-NEXUS, not separate products or competing system identities.

> **Phase 1 — RC with Disclosure (non-production). Production decision: NO-GO.** This release-candidate positioning is for transparent evaluation and continued development; it is not a Production approval, security certification, or claim that every capability is complete. A passing test subset, CI run, implemented feature, or running service does not establish Production readiness.

## Release disclosure

The release decision and gate evidence are maintained in [Release Status](RELEASE_STATUS.md), [Release Checklist](docs/RELEASE_CHECKLIST.md), and the [Q10–Q16 Closure Contract](docs/Q10_Q16_CLOSURE_CONTRACT.md).

| Gate | Disclosed state | Meaning |
|---|---|---|
| Q10 — whole security gate | **NOT_VERIFIED** | A scanner component result is not the whole gate; independent review and exact-subject evidence remain required. |
| Q11 — live AI/provider | **BLOCKED / NOT_VERIFIED** | A successful live provider request and expected sentinel must be proven against the exact release subject. |
| Q12 — delegated cgroup v2 | **BLOCKED / NOT_VERIFIED** | Required delegated Linux cgroup evidence is not established for the current subject. |
| Q13 — PostgreSQL disaster recovery | **NOT_VERIFIED / STALE SUBJECT** | Historical backup/restore evidence must be regenerated for the exact candidate. |
| Q14 — observability and operator alerts | **NOT_VERIFIED / STALE SUBJECT** | Required failure-injection and alert-receipt evidence must match the candidate. |
| Q15 — clean-machine deployment | **NOT_VERIFIED / STALE SUBJECT** | A fresh-host installation record is required for the exact artifact. |
| Q16 — final release convergence | **NOT_VERIFIED / NOT ELIGIBLE** | Depends on all mandatory prior gates, final-tree checks, reviewed merge, and immutable delivery evidence. |

**Evidence freshness rule:** evidence from another commit, source tree, runtime subject, or deployment is historical evidence—not proof for the candidate being evaluated. Reconcile the exact main SHA and release subject before reusing any report. The repository's release record contains historical subject references; do not treat those references as a verified current-main baseline without rechecking them.

## Start here

| Need | Open |
|---|---|
| Understand the system | [Unified Architecture](docs/CK_NEXUS_UNIFIED_ARCHITECTURE.md) · [Architecture](docs/ARCHITECTURE.md) |
| Run the application | [Quick start](#quick-start) · [Canonical Runtime Contract](docs/CK_NEXUS_UNIFIED_OPERATIONS_CONTRACT_V1.md) |
| See development evidence | Start the Creator App and open **/development**; API: **/api/dev-status** |
| Understand Agnes and agent governance | [Agnes Master Upgrade](docs/CK-NEXUS-AGNES-MASTER-UPGRADE.md) · [Development Council](docs/DEVELOPMENT_COUNCIL.md) |
| Configure integrations | [Integration Hub](docs/INTEGRATION_HUB.md) |
| Review security and tests | [Security Audit](docs/SECURITY_AUDIT.md) · [Test Report](docs/TEST_REPORT.md) |
| Prepare a release | [Release Status](RELEASE_STATUS.md) · [Release Checklist](docs/RELEASE_CHECKLIST.md) · [Q10–Q16 Contract](docs/Q10_Q16_CLOSURE_CONTRACT.md) |
| Prepare customer delivery | [Seller Checklist](docs/SELLER_CHECKLIST.md) |

## What CK-NEXUS provides

- **Agnes orchestration** — interprets requests, plans bounded work, coordinates specialist roles, and reports outcomes within CK-NEXUS policy.
- **Governed execution** — permission checks, human approval boundaries, isolated workspaces, bounded workers, idempotency, verification, and fail-closed controls.
- **Brain, memory, and knowledge** — session/context handling, knowledge retrieval, observations, and evidence-linked learning workflows.
- **Skills and capabilities** — discoverable capability contracts and adapters for approved tools.
- **Integration layer** — server-side connectors such as GitHub and model providers, mediated by the Credential Broker and CK-NEXUS policy.
- **Operations and evidence** — status APIs, audit records, test results, release subjects, and deployment evidence.
- **Creator Workspace** — a user-facing interface for interacting with CK-NEXUS capabilities.
- **Development Council** — five bounded advisory roles for architecture, research, product/UX, engineering/automation, and security/QA/DevOps review.

These are capability areas of the same platform. A capability is not considered Production-ready merely because its code or documentation exists; its required runtime and release evidence must also pass.

## System architecture

```text
Users / API / Creator Workspace
              |
       Agnes Orchestrator
              |
  Skills · Agents · Knowledge · Memory
              |
   CK-NEXUS Core / L3 Authority
 State · Permissions · Policy · Approvals
              |
    Governed Execution Kernel
 Queue · Sandbox · Idempotency · Verify
              |
 Approved Tool and Provider Adapters
 GitHub · Model Providers · MCP · Integrations
              |
       Evidence · Audit
       Release Gates
```

**Authority boundary:** CK-NEXUS Core / L3 Authority owns state, memory, permissions, policy, execution decisions, and evidence. External tools and workflow services are adapters only; they do not become policy or release authorities. All consequential mutations must pass the applicable CK-NEXUS permission, approval, idempotency, and verification controls.

## Agnes 5D Companion — roadmap

Agnes is the orchestration identity of CK-NEXUS. The 5D Companion is a planned presentation and interaction layer; it does not replace Core/L3 authority or independently receive execution permissions.

**Character direction:** anime-inspired companion with silver-blue hair, violet eyes, a white-and-blue technology outfit, and a friendly, helpful presence. This is a design direction, not a claim that finished character assets or a live 5D runtime are already deployed.

Planned delivery sequence:

1. **Character Bible** — identity, personality, voice, visual constraints, and expression rules.
2. **5D Visual Specification** — dimensional presentation, lighting, materials, camera, and interaction principles.
3. **Character Sheet** — consistent front, side, back, expression, and pose references.
4. **Layered production assets** — separated, named, rig-ready visual layers with provenance.
5. **Runtime format decision** — evaluate Live2D, VRM, or another suitable representation against target devices and performance.
6. **Rive interaction/state model** — map idle, listening, thinking, speaking, success, warning, and blocked states.
7. **Companion UI** — accessible chat, status, task progress, and evidence surfaces.
8. **Event Adapter** — translate approved CK-NEXUS events into presentation states; never grant authority.
9. **Core/L3 permission contract** — define exactly which actions Agnes may request, which require human approval, and which are prohibited.
10. **Runtime integration and verification** — test state transitions, permissions, accessibility, latency, resource use, and failure behavior before any release claim.

The character, UI, animation, and model layers are presentation components. Core/L3 remains the sole authority for permissions, policy, execution, and evidence.

## Quick start

Requirements: Python 3.11 or later.

Linux / macOS:

```bash
cp .env.example .env.local
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m creator_app.unified
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env.local
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m creator_app.unified
```

Open http://127.0.0.1:8000. The canonical application entry point is:

```bash
python3 -m creator_app.unified
```

Legacy launchers may remain for compatibility, but new setup instructions and deployment definitions must use the canonical entry point and the [Canonical Runtime Contract](docs/CK_NEXUS_UNIFIED_OPERATIONS_CONTRACT_V1.md).

## Runtime and developer interfaces

| Interface | Purpose |
|---|---|
| GET /health | Application health/readiness endpoint |
| GET /api/status | Redacted application and configuration status |
| GET /docs | OpenAPI reference for the running build |
| /development | Internal development and evidence dashboard |
| GET /api/dev-status | Authenticated development-status snapshot |

The running build's OpenAPI document is authoritative for the complete API surface. Do not assume an endpoint or integration is available from a roadmap or historical report alone.

## Integrations

Integrations are adapters behind CK-NEXUS capability and permission boundaries. Credentials remain server-side and are mediated by the approved credential mechanism.

The current [Integration Hub](docs/INTEGRATION_HUB.md) records the active server-side integration architecture. **n8n is retired from the active CK-NEXUS runtime**; historical workflow references describe earlier architecture and must not be presented as a current runtime dependency.

## Security and operating rules

- Keep `production_status = NO-GO` until every mandatory release gate is verified against the exact release subject and independently reviewed where required.
- Keep the MCP service bound to loopback (127.0.0.1:8765) under the current deployment contract; do not expose it directly to the public Internet.
- Keep credentials server-side in the approved credential mechanism. Never put keys, tokens, private keys, or secret values in source, README files, screenshots, or logs.
- Treat repository state, deployed runtime state, test results, and release evidence as separate facts; reconcile them before deployment.
- Do not reset, clean, overwrite, merge, or deploy over existing work without reviewing the exact diff and preserving required evidence.
- External tools have no CK-NEXUS policy authority. No evidence means no completion.

## Development lifecycle and update protocol

Use the evidence-based lifecycle:

`DESIGNED → IMPLEMENTED → EXECUTED → VERIFIED → PRODUCTION`

These states are not interchangeable. Implementation is not execution; execution is not verification; verification is not Production authorization.

**Before work:** read the latest project state and development log; verify repository, branch, exact HEAD SHA, worktree status, task scope, current evidence, and blockers. Do not assume an earlier checkout or report is current.

**After work:** record the timestamp, task/agent, previous state, changes, files, reason, exact evidence, verification performed, blockers, next action, and release impact. Link results to the exact commit and test/run identifiers.

**Continuity rules:** do not invent test results, overwrite unreviewed work, reuse stale evidence, bypass Core/L3, silently change release status, or erase blockers and reviewer decisions. If main advances during a task, recheck the diff and rebase the plan before any further write.

## Release readiness

Production promotion is fail-closed. The [Q10–Q16 Closure Contract](docs/Q10_Q16_CLOSURE_CONTRACT.md) defines the mandatory security, live-provider, sandbox, recovery, observability, clean-machine deployment, and final-release evidence.

A release claim must identify the exact source commit, source tree, runtime/deployment subject, test and security reports, and required independent review. Evidence from a different commit or runtime is historical evidence, not proof for the candidate being released.

Run the repository's release check from the intended, clean release environment:

```bash
python3 scripts/release_check.py
```

Then follow the complete [Release Checklist](docs/RELEASE_CHECKLIST.md). A successful command is one piece of evidence, not a substitute for the full release decision.

## Engineering records

Implementation phases and historical milestones (including R-series and Agnes Execution Kernel phases) are documented as engineering records under [docs/](docs/). They describe the evolution and validation of individual capabilities; they are not separate products, runtime entry points, or independent Production certifications.

Useful references:

- [Agnes Execution Kernel Phase 3](docs/AGNES_EXECUTION_KERNEL_PHASE3_HARDENED_PIPELINE.md)
- [Credential Broker and Provider Router](docs/R7_CREDENTIAL_BROKER_PROVIDER_CUTOVER.md)
- [Canonical R9–R11 Implementation](docs/R9_R11_CANONICAL_IMPLEMENTATION.md)
- [Plans and reports](docs/plans/)
- [Repository Issues](https://github.com/CK-NEXUS-AI/ck-nexus/issues)
- [Repository Actions](https://github.com/CK-NEXUS-AI/ck-nexus/actions)

---

**Product identity:** CK-NEXUS.
**AI orchestration and execution layer:** Agnes.
**Canonical application runtime:** `creator_app.unified`.
**Phase 1 positioning:** RC with Disclosure (non-production).
**Production decision:** NO-GO until every mandatory gate is verified for the exact release subject.
**Operating rule:** NO EVIDENCE → NO DONE.
