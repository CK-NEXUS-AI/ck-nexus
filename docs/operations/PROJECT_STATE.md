# CK-NEXUS Project State

> Operational checkpoint for maintainers and AI development agents. This file is not release evidence and does not override CK-NEXUS Core, the release contract, or repository policy.

## Current Snapshot

- Canonical repository: `CK-NEXUS-AI/ck-nexus`.
- Main baseline inspected: commit `4d1366cef3cbdd18aa174bdf67308567635c750a`, tree `57adfe86cd6d9bdbca5c97d336cb733df2308ae5`, commit date 2026-11-05.
- Documentation/operations workstream: `feat/agnes-persistent-ops-memory-20261110`.
- Badge automation workstream is separate: PR #364, branch `chore/auto-update-badge-system`, latest inspected commit `954c5e6c64b1f0f678fa1192476c63c7349e85d2`. Do not mix commits between these workstreams.
- PR #364 checks inspected on commit `954c5e6`: CK-NEXUS CI, preflight, attack regression, CodeQL, CodeQL quality (Python/JS/Actions), and workflow lint passed. Render/create-PR/verify-docs are skipped on pull_request by design. Cubic review was pending at last inspection. PR remained OPEN, REVIEW_REQUIRED, BLOCKED; no merge performed.
- No VPS access was performed. This checkpoint is based on repository contents and Termux/GitHub observations only.

## Product and Architecture Baseline

CK-NEXUS already contains substantial agent and governance components. Extend these; do not create a parallel authority plane.

| Capability | Existing implementation | Verified limitation / boundary |
|---|---|---|
| Repository agent guidance | `.claude/agents/{architect,scout,security,verifier}.md`, `CLAUDE.md` | Four repository agent role files; not evidence that separate live agent processes are running |
| Expert team | creator_app/ai_team/TeamDirector, Director, Engineer, Guardian, Analyst, Researcher, Designer, Connector | TeamDirector now has sync and async entry points and dispatches dependency-ready plan steps in bounded waves |
| Parallel execution | creator_app/ai_team/intelligence/parallel_executor.py; EnhancedUniversalSystem.process_parallel; ControlPlaneOrchestrator.dispatch | TeamDirector defaults to concurrency 2 (bounded 1–5), 60-second step timeout, isolated worker snapshots, deterministic coordinator integration, and per-agent locks shared across concurrent requests; timeout cannot forcibly terminate an already-running Python worker thread |
| Durable task queue | `creator_app/control_plane/task_store.py`; MCP task tools in `creator_app/agnes/mcp_server.py` | SQLite queue is implemented and tested locally; live deployment/health was not verified |
| Agent task graph | `creator_app/control_plane/orchestrator.py` | Graph planning and bounded wave dispatch exist; queue completion is not release verification |
| Shared agent knowledge | `creator_app/ai_team/shared_knowledge.py` | JSON persistence is optional; TeamDirector defaults `knowledge_path=None`, so default knowledge is process-local |
| Semantic memory | `creator_app/ai_team/intelligence/semantic_memory.py` | In-memory bounded store; not durable across process restart |
| Unified memory contract | `creator_app/unified_memory/contracts.py`, `store.py` | Current `UnifiedMemoryStore` is explicitly an in-memory reference implementation |
| Personal memory | `creator_app/personal_intelligence/memory.py` | Requires consent and TTL, but the current store is in-memory |
| MCP and tools | `creator_app/agnes/mcp_server.py`, connector fabric | External tool completion does not grant authority; retain Core policy boundary |

## Agnes Bounded Parallel Execution — Local Verification

- Work branch: feat/agnes-persistent-ops-memory-20261110; base: origin/main 4d1366cef3cbdd18aa174bdf67308567635c750a.
- Existing implementation commits: c2e7038 (async entry/settings), 8808f12 (dependency waves), 4238633 (fail-closed outcomes), 6fd0b39690ff92bfeb26789bcd145578cbb0b727 (serialize shared Agent instances across concurrent requests), 501f170be424c0352b5b76b12fb37b49b3a51bb4 (preserve plan-step identity in results).
- Reliability-guard implementation commit: `873af83ba55a97075ba00c0a9f34a1ff30865a6d` (local-only, unpushed): TaskStore durable idempotency, MCP optional idempotency-key plumbing, cooperative request cancellation, and process-wide TeamDirector worker budget (2).
- Focused regression: 151 passed, 1 warning across `creator_app/ai_team/tests` and `tests/test_control_plane_task_store.py`.
- Static checks: Ruff PASS; compileall PASS for `creator_app/ai_team`, `creator_app/control_plane`, `creator_app/agnes`; git diff --check PASS.
- Warning: PytestConfigWarning: Unknown config option: asyncio_mode from the installed pytest environment; it is not counted as a test failure.
- MCP adapter integration tests are UNVERIFIED because the Termux Python environment lacks the declared `mcp>=1.13,<2` dependency. They must run in a correctly provisioned environment before claiming adapter verification.
- Cancellation is cooperative: Python cannot forcibly terminate an already-running non-cooperative synchronous thread. Process-wide concurrency is limited to one Python process; there is no cross-process/host budget.
- The branch is local-only and has not been pushed or merged. No VPS, production or external mutation was performed. WQ-005 remains PARTIAL and Production remains NO-GO.

## Release Snapshot

- Production decision remains **NO-GO**.
- Current main baseline is `4d1366c`; the checked-in `RELEASE_STATUS.md` still refers to older main `22edd1f` and earlier subjects. Treat that document as stale until reconciled through the release process.
- The current main evidence JSON records source SHAs that do not match `4d1366c`: Q10/Q11/Q13/Q14/Q15/Q16 image use `4cf17cd`; Q12 uses `512837c`; Q16 runtime-license uses `4cf17cd`. These are historical records, not evidence for current main.
- Q11 evidence is BLOCKED. Q12 PASS, Q13 PASS_CANDIDATE, Q14 PASS, Q15 PASS_CANDIDATE, Q16 image PASS_CANDIDATE and runtime-license PASS are all bound to other source identities and cannot promote current main.
- Q10 dependency audit JSON has no top-level result/status field in the inspected summary; do not infer a whole-gate PASS.
- Recompute the current release subject and re-run/reconcile every mandatory gate against one exact candidate SHA/tree before any production claim.

## Working Rules

1. Read this checkpoint and `WORK_QUEUE.md` before starting a new session.
2. Follow `CLAUDE.md`, `docs/Q10_Q16_CLOSURE_CONTRACT.md`, and the applicable runbooks as authorities.
3. Keep all work on isolated feature branches/worktrees. Never overwrite unrelated dirty work.
4. No evidence means no completion. A test pass, badge, SHA match, or queue completion is not production verification.
5. Never expose secrets in files, commands, output, logs, or evidence.
6. Do not weaken Core/L3 authority, policy gates, runner allow-lists, or approval requirements.
7. External tools remain `authority_level=NONE`; n8n remains workflow plane only.
8. Never claim an agent, provider, service, or VPS was used unless its execution was observed.
