# CK-NEXUS Hybrid Fast Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing CK-NEXUS control plane faster by adding bounded fast-path routing, resource-aware parallel probes, and short-lived safe caching without weakening execution policy.

**Architecture:** Extend the existing `creator_app/control_plane` seam rather than adding another orchestrator. A deterministic fast policy handles known failures first; independent read-only probes use a bounded executor; only unresolved cases are eligible for AI diagnosis, which returns recommendations that are mapped to predefined action IDs. Verification remains mandatory.

**Tech Stack:** Python 3.12, existing `ParallelExecutor`, pytest, existing CK-NEXUS control-plane and health contracts.

**Spec:** `docs/specs/2026-10-23-hybrid-fast-control-plane-design.md`

## Global Constraints

- Work directly in `/root/ck-nexus` and preserve existing user changes.
- Never print or persist API keys, tokens, credentials, or secret values.
- Do not execute model-generated shell commands directly.
- Default control-plane concurrency is `2`; do not exceed `3` without fresh capacity evidence.
- Read-only cache TTL is `5` seconds; mutating/failed operations must not be cached.
- Existing watchdog rate limits, verification gates, and loopback-only MCP boundary remain unchanged.
- Do not start `ck-auditor` as part of this feature; exit 137 requires separate resource diagnosis.
- Do not commit or push unless separately authorized.

## Review Focus

- A known failure must use the deterministic fast path without invoking AI diagnosis.
- An unknown failure must not execute model-generated command text.
- Concurrent probes must respect the configured concurrency ceiling.
- Expired cache entries must trigger a fresh probe rather than returning stale health.
- A failed/mutating operation must never be served from the read-only cache.

---

### Task 1: Add deterministic fast-path policy

**Files:**
- Create: `creator_app/control_plane/fast_policy.py`
- Test: `tests/test_control_plane_fast_policy.py`

**Interfaces:**
- Produces `FastDecision` with `handled: bool`, `action_id: str | None`, `reason: str`.
- Public function: `decide_fast(signal: str) -> FastDecision`.
- Known action IDs are identifiers only; they do not contain shell text.

- [ ] **Step 1: Write the failing tests**

Test known watchdog/service/container failure signals map to predefined action IDs, unknown signals return `handled=False`, and action IDs never contain shell metacharacters or commands.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python -m pytest -q tests/test_control_plane_fast_policy.py`
Expected: non-zero failure because `creator_app.control_plane.fast_policy` does not yet exist.

- [ ] **Step 3: Implement the minimal policy**

Use an explicit dictionary of known signals to action IDs. Do not parse arbitrary shell commands. Keep unknown input unhandled so the caller can escalate to diagnosis.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `python -m pytest -q tests/test_control_plane_fast_policy.py`
Expected: all focused tests pass.

- [ ] **Step 5: Run the existing control-plane suite**

Run: `python -m pytest -q tests/test_control_plane.py tests/test_control_plane_integration.py`
Expected: existing tests remain green.

---

### Task 2: Add bounded parallel health probing with resource budget

**Files:**
- Create: `creator_app/control_plane/fast_probe.py`
- Test: `tests/test_control_plane_fast_probe.py`

**Interfaces:**
- Public class: `FastProbeRunner(max_concurrency: int = 2)`.
- Public async method: `run(probes: dict[str, Callable[[], Awaitable[Any] | Any]]) -> dict[str, ProbeResult]`.
- `ProbeResult` records status, elapsed milliseconds, and redacted error text only.

- [ ] **Step 1: Write failing tests**

Test independent probes run concurrently, concurrency never exceeds 2 by default, one failing probe does not prevent unrelated probes, and an empty probe set returns immediately.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest -q tests/test_control_plane_fast_probe.py`
Expected: non-zero failure because the new probe runner does not exist.

- [ ] **Step 3: Implement the minimal runner**

Use asyncio tasks with a semaphore or the existing `ParallelExecutor` contract. Do not create unbounded tasks. Capture monotonic elapsed time and return redacted failure metadata.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python -m pytest -q tests/test_control_plane_fast_probe.py`
Expected: all focused tests pass.

- [ ] **Step 5: Run related executor tests**

Run: `python -m pytest -q tests/test_control_plane_integration.py tests/test_control_plane_worker.py`
Expected: existing executor/control-plane behavior remains green.

---

### Task 3: Add 5-second read-only health cache

**Files:**
- Create: `creator_app/control_plane/fast_cache.py`
- Test: `tests/test_control_plane_fast_cache.py`

**Interfaces:**
- Public class: `ReadOnlyTTLCache(ttl_seconds: float = 5.0)`.
- Public methods: `get(key)`, `put(key, value, *, cacheable=True)`, `invalidate(key)`, `clear()`.
- Cache stores timestamps internally and never stores exceptions or mutation results.

- [ ] **Step 1: Write failing tests**

Test cache hit inside TTL, miss after TTL, invalidation, and rejection of non-cacheable values.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest -q tests/test_control_plane_fast_cache.py`
Expected: non-zero failure because the cache class does not yet exist.

- [ ] **Step 3: Implement the minimal TTL cache**

Use `time.monotonic()` for expiry. Store only explicitly cacheable read-only values. Never serialize secrets into cache metadata.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python -m pytest -q tests/test_control_plane_fast_cache.py`
Expected: all focused tests pass.

- [ ] **Step 5: Run health/control-plane regression tests**

Run: `python -m pytest -q tests/test_health_model.py tests/test_control_plane.py tests/test_control_plane_integration.py`
Expected: all pass.

---

### Task 4: Integrate fast policy, probes and cache into the existing orchestrator

**Files:**
- Modify: `creator_app/control_plane/orchestrator.py`
- Modify: `creator_app/control_plane/__init__.py` only if public exports are needed
- Test: `tests/test_control_plane_fast_integration.py`

**Interfaces:**
- `ControlPlaneOrchestrator.fast_path(signal)` returns `FastDecision`.
- `ControlPlaneOrchestrator.fast_probe(...)` delegates to the bounded probe runner.
- `ControlPlaneOrchestrator.health_cached(...)` reads/updates only the read-only TTL cache.
- AI diagnosis remains outside the fast path and cannot directly execute commands.

- [ ] **Step 1: Write failing integration tests**

Test known signal → action ID without diagnosis, unknown signal → unhandled, parallel probe execution capped at 2, and cached health avoids a duplicate probe inside 5 seconds.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest -q tests/test_control_plane_fast_integration.py`
Expected: non-zero failure because orchestrator fast-path interfaces do not yet exist.

- [ ] **Step 3: Implement the minimum integration**

Compose the three small components into the existing orchestrator. Preserve current `dispatch()` semantics and default `ParallelExecutor(max_concurrency=3)` for the existing task graph unless the new fast-probe path is explicitly used; do not silently change unrelated concurrency behavior.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `python -m pytest -q tests/test_control_plane_fast_integration.py`
Expected: all focused integration tests pass.

- [ ] **Step 5: Run the complete relevant regression suite**

Run: `python -m pytest -q tests/test_control_plane.py tests/test_control_plane_integration.py tests/test_control_plane_task_store.py tests/test_control_plane_worker.py tests/test_control_plane_verification.py tests/test_control_plane_mcp.py tests/test_control_plane_fast_policy.py tests/test_control_plane_fast_probe.py tests/test_control_plane_fast_cache.py tests/test_control_plane_fast_integration.py`
Expected: all relevant tests pass.

---

### Task 5: Operational verification and performance evidence

**Files:**
- Create: `docs/evidence/2026-10-23-hybrid-fast-control-plane-verification.md`
- No production code changes unless a test exposes a real defect.

**Interfaces:**
- Evidence records only timing/status metrics and redacted identifiers.

- [ ] **Step 1: Run repository checks**

Run: `python -m pytest -q` and `ruff check .` and `git diff --check`.
Expected: no regressions attributable to this change.

- [ ] **Step 2: Run live core health checks**

Verify scanner `127.0.0.1:8787/health`, gateway `127.0.0.1:8790/health`, workflow UI `127.0.0.1:8791/api/health`, n8n `127.0.0.1:5678/healthz`, watchdog timer active, and Git dirty state preserved.

- [ ] **Step 3: Capture performance evidence**

Measure one known-fast-path decision, one parallel probe batch, and one cache hit. Record timings without secrets. Do not claim a numeric speedup unless a baseline and after measurement are both available.

- [ ] **Step 4: Final verification**

Run `git diff --check`, inspect `git status --short`, and confirm the pre-existing `ops/vps/services/cknexus_n8n_workflows_ui.py` modification remains untouched.

## Execution Notes

- The current VPS has only ~1.9 GiB RAM and active swap pressure. Resource protection takes priority over theoretical maximum parallelism.
- `ck-auditor` exit 137 is outside this feature. Diagnose it separately before enabling automatic restart beyond the watchdog's existing bounded behavior.
- Qwen/Model Studio currently returns upstream 401 invalid API key. This feature must remain usable without Qwen and must not wait for that credential to become valid.
- No commit or push is part of this plan.
