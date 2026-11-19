# Autonomous Repair Worker Implementation Plan

> **For agentic workers:** Use the host's available task-by-task implementation workflow. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bounded Autonomous Repair Worker that consumes the existing durable task queue, executes only approved sandbox handlers, verifies results with evidence, retries within a fixed repair budget, and never authorizes production mutation.

**Architecture:** Add a small worker module in `creator_app/control_plane/` that owns the queue-to-verification lifecycle and delegates actual task behavior through an explicit handler interface. Reuse `TaskStore`, `ControlPlaneVerifier`, and `ControlPlaneOrchestrator`; do not duplicate queue, planning, or verification logic. The worker persists checkpoints before and after execution and converts lease loss, timeout, handler failure, verification failure, and exhausted retries into deterministic task outcomes.

**Tech Stack:** Python 3.12, existing SQLite `TaskStore`, pytest, existing CK-NEXUS control-plane models and verification seam.

## Global Constraints

- Work directly in `/root/ck-nexus`; preserve all unrelated dirty changes.
- No model inference, Model Studio calls, paid-provider calls, or credential access.
- Production mutation remains disabled: `external_mutation_authorized=False`, `production_status=NO-GO`, `release_evidence=False` until the existing verification gate explicitly returns verified evidence; this phase still does not perform production mutation.
- Queue leases are authoritative; stale workers must be fenced from checkpoint/finish operations.
- Repair attempts are bounded; no unbounded retry loop.
- Worker execution must be deterministic and testable through injected handlers/verifiers.
- Evidence references must be non-empty before a task can be considered verified.
- Existing `TaskStore` and `ControlPlaneVerifier` contracts remain backward compatible.

---

### Task 1: Add the worker contract and red-green lifecycle tests

**Files:**
- Create: `creator_app/control_plane/worker.py`
- Modify: `tests/test_control_plane_integration.py`
- Test: `tests/test_control_plane_worker.py`

**Interfaces:**
- Consumes: `TaskStore.claim_next`, `TaskStore.save_checkpoint`, `TaskStore.finish`, `ControlPlaneVerifier.evaluate`, `ControlPlaneVerifier.repair_loop`.
- Produces: `RepairWorker`, `WorkerResult`, and an injected `TaskHandler` protocol/callable contract.

- [ ] **Step 1: Add the focused failing tests**

Cover these observable cases: successful queued task claims a lease, records an execution checkpoint, verifies with non-empty evidence, and finishes completed; handler failure produces a failed task without release evidence; verifier failure invokes at most the configured repair budget; a stale/expired lease cannot be completed; empty evidence never produces verified/release evidence; handler timeout becomes failed; worker result always reports `production_status=NO-GO` and `external_mutation_authorized=False`.

- [ ] **Step 2: Verify the relevant failure**

Run: `cd /root/ck-nexus && pytest -q tests/test_control_plane_worker.py`
Expected: collection succeeds and the new behavioral tests fail because `creator_app.control_plane.worker` and its worker contract do not yet exist.

- [ ] **Step 3: Implement the minimum worker contract**

Define a worker that accepts an existing `TaskStore`, verifier, handler registry, worker id, execution timeout, and repair-attempt limit. Claim one task at a time, checkpoint state before handler execution, invoke only the selected injected handler, checkpoint the handler outcome, require evidence for verification, and finish using the same lease token. Convert lease conflicts and handler exceptions into bounded failures without bypassing the queue.

- [ ] **Step 4: Verify the focused pass**

Run: `cd /root/ck-nexus && pytest -q tests/test_control_plane_worker.py`
Expected: all worker lifecycle tests pass.

- [ ] **Step 5: Run affected integration checks**

Run: `cd /root/ck-nexus && pytest -q tests/test_control_plane_task_store.py tests/test_control_plane_verification.py tests/test_control_plane_integration.py`
Expected: all selected control-plane tests pass with no regressions.

- [ ] **Step 6: Commit the passing deliverable**

Do not commit automatically; the repository already contains unrelated user changes and this plan explicitly preserves them.

### Task 2: Add bounded repair and checkpoint semantics

**Files:**
- Modify: `creator_app/control_plane/worker.py`
- Test: `tests/test_control_plane_worker.py`

**Interfaces:**
- Consumes: `RepairWorker.run_once`, `ControlPlaneVerifier.repair_loop`, and the task payload's repair/verification context.
- Produces: deterministic checkpoint states `claimed`, `executing`, `verifying`, `repairing`, `completed`, or `failed`, plus bounded attempt metadata.

- [ ] **Step 1: Add failing repair tests**

Assert a verification failure can trigger a repair callback only up to the configured maximum; the worker finishes failed after exhaustion; a successful repair must re-run verification; and a worker exception during repair does not escape the bounded loop or mark release evidence true.

- [ ] **Step 2: Verify red**

Run: `cd /root/ck-nexus && pytest -q tests/test_control_plane_worker.py -k repair`
Expected: repair lifecycle assertions fail before the bounded repair implementation exists.

- [ ] **Step 3: Implement minimum bounded repair behavior**

Use the existing verifier's bounded repair seam. Persist a checkpoint before each repair attempt. Never apply a production patch from the worker. On successful verification, finish completed with evidence refs; on exhaustion or infrastructure failure, finish failed with an error and `release_evidence=False`.

- [ ] **Step 4: Verify green**

Run: `cd /root/ck-nexus && pytest -q tests/test_control_plane_worker.py -k repair`
Expected: all repair tests pass.

- [ ] **Step 5: Run control-plane regression**

Run: `cd /root/ck-nexus && pytest -q tests/test_control_plane_worker.py tests/test_control_plane_mcp.py tests/test_control_plane_task_store.py tests/test_control_plane_verification.py`
Expected: all selected tests pass.

### Task 3: Connect the worker to the existing orchestrator without enabling production execution

**Files:**
- Modify: `creator_app/control_plane/orchestrator.py`
- Modify: `creator_app/control_plane/models.py`
- Test: `tests/test_control_plane_worker.py`
- Test: `tests/test_control_plane_integration.py`

**Interfaces:**
- Consumes: `ControlPlaneOrchestrator.plan`, `TaskGraph`, and `RepairWorker`.
- Produces: a queue payload adapter that preserves role/dependency metadata and explicitly marks the graph as non-production.

- [ ] **Step 1: Add failing integration tests**

Assert an orchestrator-produced task graph can be serialized into a queue payload and consumed by the worker handler registry without inventing a second planning path. Assert dependency metadata is preserved and no node can set production mutation authorization.

- [ ] **Step 2: Verify red**

Run: `cd /root/ck-nexus && pytest -q tests/test_control_plane_worker.py tests/test_control_plane_integration.py -k orchestrator`
Expected: new adapter assertions fail because the worker/orchestrator integration seam is absent.

- [ ] **Step 3: Implement the minimum adapter**

Add a narrow adapter method that converts a planned `TaskGraph` into queue-safe payload metadata. Keep execution in the worker and planning in the orchestrator. Do not call `TeamDirector.process_request` from the queue boundary unless the injected handler explicitly selects it; no external inference is introduced by this change.

- [ ] **Step 4: Verify green**

Run: `cd /root/ck-nexus && pytest -q tests/test_control_plane_worker.py tests/test_control_plane_integration.py -k orchestrator`
Expected: all integration assertions pass.

- [ ] **Step 5: Run affected regression suite**

Run: `cd /root/ck-nexus && pytest -q tests/test_control_plane.py tests/test_control_plane_routing.py tests/test_control_plane_integration.py tests/test_control_plane_worker.py`
Expected: all selected tests pass.

### Task 4: Live-safe canary and final verification

**Files:**
- Test: existing repository test suite and live MCP canary commands

**Interfaces:**
- Consumes: deployed `TaskStore`, worker contract, existing MCP task lifecycle, and health checks.
- Produces: evidence that one sandbox-only canary can move through queue → worker → verification without exposing credentials or mutating production.

- [ ] **Step 1: Add/adjust a live-safe canary test**

Use a unique canary job id and an injected deterministic handler that returns a local result plus a non-secret evidence reference. The canary must not call Model Studio, modify production resources, or expose the lease token in status output.

- [ ] **Step 2: Run focused canary verification**

Run: `cd /root/ck-nexus && pytest -q tests/test_control_plane_worker.py tests/test_control_plane_mcp.py`
Expected: focused worker/MCP suite passes.

- [ ] **Step 3: Run repository verification**

Run: `cd /root/ck-nexus && pytest -q && ruff check . && python3 -m compileall -q creator_app && git diff --check`
Expected: pytest has zero failures; Ruff exits 0; compileall exits 0; git diff check exits 0.

- [ ] **Step 4: Run operational health verification**

Run the existing `scripts/ck-health` and verify `cknexus-mcp.service`, `cknexus-api-gateway.service`, `cknexus-scanner.service`, and `cknexus-watchdog.timer` are active and MCP remains loopback-only at `127.0.0.1:8765`.

- [ ] **Step 5: Record the execution ledger**

Record task completion and verification in the dated evidence bundle for this plan. Keep `RELEASE_STATUS.md` limited to current release-gate status; do not recreate a root progress ledger.

## Unresolved externally observable decisions

- Whether a future production-enabled phase should allow worker handlers to mutate production remains outside this phase and requires a separate explicit authorization boundary.
- Whether a future worker should process multiple tasks per invocation remains deferred; this phase processes one claimed task per `run_once` to keep leases, checkpoints, and failure attribution deterministic.
