# n8n Development Intelligence Auto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collect n8n execution telemetry into a safe, deduplicated CK-NEXUS development queue automatically.

**Architecture:** Add a small deterministic Python intelligence package, a short-lived collector, a restricted n8n read adapter, a SQLite event ledger, and a systemd timer. The collector feeds the existing `TaskStore`; it never executes shell/Git commands and never grants production mutation authority.

**Tech Stack:** Python 3.12, stdlib `sqlite3`, `urllib`, `hashlib`, `systemd`, existing CK-NEXUS `TaskStore`, pytest, Ruff.

**Spec:** `docs/specs/2026-10-24-n8n-development-intelligence-auto-design.md`

## Global Constraints

- Preserve all existing user changes; do not use `git add -A`.
- Collector concurrency is exactly 1.
- Poll interval defaults to 120 seconds.
- Maximum executions processed per cycle is 50.
- Slow execution threshold defaults to 30 seconds.
- Repeated failure threshold defaults to 3 observations.
- n8n integration is read-only.
- Generated tasks must set `production_status=NO-GO` and `external_mutation_authorized=false`.
- No API key or authorization header may be written to logs or persisted event data.
- Collector database must be outside tracked source and mode `0600`.
- No direct `git`, `docker`, `systemctl`, or arbitrary subprocess execution from the collector.

## Review Focus

- Malformed n8n execution objects must be ignored without creating development tasks.
- Secret-bearing error text must be sanitized before persistence or logging.
- Repeated polling of the same execution must remain idempotent.
- Remote authentication/transport failure must fail closed without creating tasks.
- Task payloads must remain typed and non-production even when the input contains command-like text.

### Task 1: Normalized n8n intelligence contracts

**Files:**
- Create: `creator_app/n8n_intelligence/__init__.py`
- Create: `creator_app/n8n_intelligence/models.py`
- Test: `tests/test_n8n_intelligence_models.py`

**Interfaces:**
- Produces `N8NExecutionEvent`, `DevelopmentSignal`, and bounded enum/value contracts used by all later tasks.

- [ ] **Step 1: Write failing tests** for valid event construction, bounded severity/category, and deterministic serialization.
- [ ] **Step 2: Run `pytest tests/test_n8n_intelligence_models.py -q` and verify the expected missing-module failure.**
- [ ] **Step 3: Implement minimal immutable dataclasses and validation.**
- [ ] **Step 4: Run the targeted tests and verify PASS.**
- [ ] **Step 5: Run targeted Ruff on the new files.**

### Task 2: Sanitizer, fingerprint, classifier, and priority engine

**Files:**
- Create: `creator_app/n8n_intelligence/analysis.py`
- Test: `tests/test_n8n_intelligence_analysis.py`

**Interfaces:**
- `sanitize_message(text: str) -> str`
- `fingerprint_execution(execution: dict[str, object]) -> str`
- `classify_execution(execution: dict[str, object], slow_seconds: float) -> DevelopmentSignal | None`
- `priority_for(signal: DevelopmentSignal, repeat_count: int) -> int`

- [ ] **Step 1: Write failing tests** for token/API-key redaction, bounded message length, stable fingerprint, success suppression, failure classification, slow classification, and repeat priority escalation.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement deterministic analysis using only stdlib.**
- [ ] **Step 4: Run targeted tests and verify GREEN.**
- [ ] **Step 5: Run Ruff.**

### Task 3: SQLite intelligence ledger

**Files:**
- Create: `creator_app/n8n_intelligence/store.py`
- Test: `tests/test_n8n_intelligence_store.py`

**Interfaces:**
- `N8NIntelligenceStore(database: str | Path)`
- `record_event(event: N8NExecutionEvent) -> tuple[bool, int]`
- `checkpoint() -> str | None`
- `set_checkpoint(value: str) -> None`
- `close()` is not required; use short-lived connections internally.

- [ ] **Step 1: Write failing tests** for schema creation, mode/permissions, first insert, duplicate insert, repeat counter, and checkpoint persistence.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement WAL-backed SQLite storage with unique fingerprint constraint.**
- [ ] **Step 4: Run targeted tests and verify GREEN.**
- [ ] **Step 5: Run Ruff.**

### Task 4: Safe development-task adapter

**Files:**
- Create: `creator_app/n8n_intelligence/task_bridge.py`
- Test: `tests/test_n8n_intelligence_task_bridge.py`

**Interfaces:**
- `build_task(signal: DevelopmentSignal, repeat_count: int) -> tuple[str, dict[str, object]]`
- The returned payload must use handler `n8n_development_signal`, `production_status=NO-GO`, `external_mutation_authorized=false`, and contain no shell command field.

- [ ] **Step 1: Write failing tests** for deterministic job IDs, safe payload fields, priority mapping, and command-like input rejection.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement typed task construction only.**
- [ ] **Step 4: Run targeted tests and verify GREEN.**
- [ ] **Step 5: Run Ruff.**

### Task 5: Restricted n8n read client

**Files:**
- Create: `creator_app/n8n_intelligence/client.py`
- Test: `tests/test_n8n_intelligence_client.py`

**Interfaces:**
- `N8NReadClient(base_url: str, key_file: Path, timeout: float = 10.0, max_items: int = 50)`
- `list_executions(cursor: str | None = None) -> tuple[list[dict[str, object]], str | None]`

- [ ] **Step 1: Write failing tests** for URL/path allowlisting, GET-only behavior, auth-file handling, response size/item bound, malformed JSON, and HTTP failure mapping.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement urllib-based read-only client; never expose key in exceptions.**
- [ ] **Step 4: Run targeted tests and verify GREEN.**
- [ ] **Step 5: Run Ruff.**

### Task 6: Collector orchestration

**Files:**
- Create: `creator_app/n8n_intelligence/collector.py`
- Test: `tests/test_n8n_intelligence_collector.py`

**Interfaces:**
- `CollectorConfig.from_env() -> CollectorConfig`
- `N8NIntelligenceCollector(...).run_once() -> CollectorReport`

**Behavior:** fetch bounded executions, normalize/classify, record event, enqueue a task only for a new actionable signal, and advance the checkpoint only after successful processing.

- [ ] **Step 1: Write failing integration-style tests** proving one failed execution creates one task, duplicate polling creates zero additional tasks, and client failure creates no tasks.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement orchestration using injected client/store/task-store dependencies.**
- [ ] **Step 4: Run targeted tests and verify GREEN.**
- [ ] **Step 5: Run targeted Ruff.**

### Task 7: CLI and systemd automation

**Files:**
- Create: `ops/vps/scripts/cknexus_n8n_intelligence.py`
- Create: `ops/vps/systemd/cknexus-n8n-intelligence.service`
- Create: `ops/vps/systemd/cknexus-n8n-intelligence.timer`
- Test: `tests/test_n8n_intelligence_cli.py`

- [ ] **Step 1: Write failing CLI tests** for successful run, failure exit code, and no secret output.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Implement short-lived CLI with a process lock and environment-configured base URL/key path/database.**
- [ ] **Step 4: Add systemd service with `NoNewPrivileges`, private temporary directory, read-only collector configuration, and timer interval of 120 seconds.**
- [ ] **Step 5: Run targeted tests and verify GREEN.**
- [ ] **Step 6: Run `git diff --check` and targeted Ruff.**

### Task 8: Production activation and verification

**Files:**
- Modify only the deployment/config files needed for activation.
- Preserve `ops/vps/services/cknexus_n8n_workflows_ui.py` and all current Fast Control changes.

- [ ] **Step 1: Install/enable the systemd timer only after unit syntax validation.**
- [ ] **Step 2: Run one manual collector cycle.**
- [ ] **Step 3: Verify timer status, service exit status, ledger creation, and TaskStore result without exposing credentials.**
- [ ] **Step 4: Run targeted tests plus existing Fast Control tests.**
- [ ] **Step 5: Run `git diff --check`.**
- [ ] **Step 6: Record evidence and report exact operational state.**

No commit or push is performed by this feature implementation unless separately authorized by the user; the future Auto-GitOps layer will consume verified development outcomes through its own gate.
