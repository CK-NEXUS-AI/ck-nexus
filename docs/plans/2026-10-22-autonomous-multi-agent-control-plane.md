# CK-NEXUS Autonomous Multi-Agent Control Plane Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify the existing TeamDirector, UniversalSystem, DevAssistantFabric, execution kernel, MCP dispatch, sandbox, model routing, Watchdog, and evidence systems behind one bounded task-graph control plane invoked by `@ai`.

**Architecture:** Preserve existing authorities instead of adding a second orchestrator. A new thin control-plane seam will normalize a request into a bounded task graph, route each workstream to existing TeamDirector/DevAssistantFabric/parallel execution capabilities, and hand execution only to the existing fail-closed execution kernel. Verification and evidence remain mandatory gates; planning never implies execution.

**Tech Stack:** Python 3.12, existing CK-NEXUS AI Team, AGNES execution kernel, MCP, pytest, Ruff, existing evidence/audit and health scripts.

## Global Constraints

- Work directly in `/root/ck-nexus`.
- Preserve all pre-existing modified and untracked files; do not use `git reset --hard`, `git clean`, destructive checkout, or unrelated overwrite operations.
- Do not print or persist secret values, API keys, tokens, or credential contents.
- Do not expose the loopback MCP listener to the public Internet.
- Existing execution policy remains fail-closed: assistants are workers, not authority.
- External assistants must not receive direct production mutation authority.
- Use existing TeamDirector, UniversalSystem, ParallelExecutor, DevAssistantFabric, sandbox executor, provider routing, Watchdog, and evidence components where their contracts already fit.
- No new orchestration framework, MCP framework, watchdog, or sandbox framework is required by this plan.
- Every new externally observable behavior gets focused tests and is verified before completion.
- `@ai` is an orchestration convention at the ChatGPT layer; CK-NEXUS exposes an equivalent dispatch/control seam but must not claim native OpenClaw invocation until the OpenClaw Gateway is actually operational.

---

### Task 1: Add the Control-Plane Task Graph seam

**Files:**
- Create: `creator_app/control_plane/__init__.py`
- Create: `creator_app/control_plane/models.py`
- Create: `creator_app/control_plane/orchestrator.py`
- Test: `tests/test_control_plane.py`

**Interfaces:**
- Consumes: request text, priority, existing `DevAssistantFabric`, existing `TeamDirector` capability metadata.
- Produces: `ControlPlaneRequest`, `TaskNode`, `TaskGraph`, and `ControlPlaneOrchestrator.plan()` with explicit `PLANNED_NOT_EXECUTED` state.

- [ ] **Step 1: Add the focused failing test**

Add tests asserting that a development request produces deterministic research/implementation/verification/security nodes, dependencies are explicit, empty requests are rejected, and the plan is never marked executable or production-safe.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m pytest -q tests/test_control_plane.py`
Expected: non-zero failure because `creator_app.control_plane` and its public interfaces do not yet exist.

- [ ] **Step 3: Implement the minimum behavior**

Create immutable dataclasses/enums for request, node, graph, node status, and execution state. The planner should use capability routing metadata from `DevAssistantFabric` and existing team roles without executing a provider. Dependencies must make verification depend on implementation and security/review depend on the implementation result. Keep production status `NO-GO` and mutation authorization false for plans.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m pytest -q tests/test_control_plane.py`
Expected: all focused control-plane tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `python -m pytest -q creator_app/dev_assistants/tests/test_fabric.py creator_app/ai_team/tests/test_intelligence.py`
Expected: existing fabric and parallel-executor contracts remain green.

- [ ] **Step 6: Commit the passing deliverable**

Do not commit automatically in this session; preserve the user's existing dirty worktree and leave integration to the user's explicit commit instruction.

---

### Task 2: Connect the graph to existing AI Team and parallel execution

**Files:**
- Modify: `creator_app/ai_team/team_director.py`
- Modify: `creator_app/ai_team/universal_system.py`
- Modify: `creator_app/control_plane/orchestrator.py`
- Test: `tests/test_control_plane_integration.py`

**Interfaces:**
- Consumes: `TaskGraph` from Task 1, existing TeamDirector and EnhancedUniversalSystem.
- Produces: bounded dispatch results with per-node status and no authority escalation.

- [ ] **Step 1: Add the focused failing test**

Assert that independent graph nodes can be grouped for `ParallelExecutor`, dependent nodes wait for prerequisites, and a failed node prevents downstream execution unless the existing bounded repair path reports success.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m pytest -q tests/test_control_plane_integration.py`
Expected: non-zero failure on the missing control-plane dispatch seam.

- [ ] **Step 3: Implement the minimum behavior**

Add a dispatcher adapter that delegates planning/agent work to existing TeamDirector and parallel execution rather than introducing another agent runtime. Preserve bounded concurrency, timeout, and existing provider circuit-breaker behavior. Record state transitions in memory for the request and expose redacted results only.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m pytest -q tests/test_control_plane_integration.py`
Expected: all graph dispatch tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `python -m pytest -q creator_app/ai_team/tests/test_team.py creator_app/ai_team/tests/test_universal.py creator_app/ai_team/tests/test_intelligence.py`
Expected: all existing AI Team, UniversalSystem, and intelligence tests pass.

- [ ] **Step 6: Commit the passing deliverable**

Do not commit automatically; preserve the dirty worktree.

---

### Task 3: Add verification/repair/evidence gates without bypassing the execution kernel

**Files:**
- Modify: `creator_app/control_plane/orchestrator.py`
- Modify: `creator_app/dev_assistants/execution.py`
- Modify: `creator_app/agnes/execution/dispatcher.py` only if a narrow adapter is required by existing public interfaces
- Test: `tests/test_control_plane_verification.py`

**Interfaces:**
- Consumes: control-plane node results and existing sandbox/execution/evidence contracts.
- Produces: bounded repair attempts, final verification state, evidence references, and explicit `NO-GO` for unverified or unauthorized changes.

- [ ] **Step 1: Add the focused failing test**

Test success, test failure followed by a bounded repair attempt, exhausted retry limit, evidence generation, and refusal to treat `EXECUTED_UNVERIFIED` as release evidence.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m pytest -q tests/test_control_plane_verification.py`
Expected: non-zero failure because the control-plane verification state machine does not yet exist.

- [ ] **Step 3: Implement the minimum behavior**

Reuse the existing sandbox executor, dynamic/patch verifier, execution dispatcher, kill switches, idempotency, and evidence builder. Never apply or commit an assistant patch from the control plane. Repair attempts are bounded by a fixed per-task maximum and stop on authorization, sandbox, credential, or evidence failures.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m pytest -q tests/test_control_plane_verification.py`
Expected: all verification and repair tests pass.

- [ ] **Step 5: Run the affected integration check**

Run: `python -m pytest -q tests/test_omni_evidence.py tests/test_omni_runtime_production_gate.py creator_app/sandbox_executor/tests/test_executor.py`
Expected: all execution/evidence/security gate tests pass.

- [ ] **Step 6: Commit the passing deliverable**

Do not commit automatically; preserve the dirty worktree.

---

### Task 4: Expose the control plane through existing auto-dispatch/MCP and operational evidence

**Files:**
- Modify: `creator_app/agnes/mcp_server.py`
- Modify: `creator_app/skills/cknexus-auto-dispatch/SKILL.md`
- Create: `tests/test_control_plane_mcp.py`
- Create: `docs/integrations/AUTONOMOUS_CONTROL_PLANE.md`

**Interfaces:**
- Consumes: existing `cknexus_auto_dispatch` request path and Task Graph control-plane interface.
- Produces: a single CK-NEXUS control-plane invocation path with plan/execute/verify state explicitly represented and evidence references returned without secrets.

- [ ] **Step 1: Add the focused failing test**

Assert that an auto-dispatch development request routes through the control plane, a normal question remains on the provider-reply path, and a planning-only request reports `PLANNED_NOT_EXECUTED` rather than pretending to execute.

- [ ] **Step 2: Verify the relevant failure**

Run: `python -m pytest -q tests/test_control_plane_mcp.py`
Expected: non-zero failure because MCP does not yet expose the unified control-plane result contract.

- [ ] **Step 3: Implement the minimum behavior**

Wire the existing auto-dispatch tool to the control-plane seam without changing its security boundary. Keep MCP loopback-only and retain existing provider status/redaction behavior. Update the OpenClaw skill instructions to call the unified control-plane path only when an authenticated MCP connection is actually available.

- [ ] **Step 4: Verify the focused pass**

Run: `python -m pytest -q tests/test_control_plane_mcp.py tests/test_mcp_auto_dispatch.py`
Expected: all focused MCP/control-plane tests pass.

- [ ] **Step 5: Run the full verification suite**

Run: `python -m pytest -q && ruff check . && ruff format --check . && git diff --check && ./scripts/ck-health`
Expected: tests/lint/format/diff checks pass; health may retain documented infrastructure warnings such as disk/systemd/OpenClaw runtime status without being misreported as a clean health state.

- [ ] **Step 6: Commit the passing deliverable**

Do not commit automatically; preserve the user's current branch and dirty worktree.

---

## Execution Handoff

The repository is already available through Remote Desktop Commander on the VPS. Execute these tasks inline in order, using the existing worktree and preserving all unrelated changes. The implementation must follow the TDD red-green-refactor cycle for each new externally observable behavior. Use the existing CK-NEXUS evidence directory for verification artifacts and never print credentials.

## Unresolved externally observable decisions

- Whether a future successful verified patch should be automatically applied to the canonical checkout remains governed by the existing human/production approval boundary and is intentionally not changed by this plan.
- Whether OpenClaw should become the native front door remains unresolved until its Gateway can start and pass a real MCP invocation test; this plan therefore keeps `cknexus_auto_dispatch` as the verified control-plane entry point.
