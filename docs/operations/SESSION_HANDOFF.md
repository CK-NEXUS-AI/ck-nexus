# CK-NEXUS Session Handoff

> Start here when continuing work in a new ChatGPT session. Read this file, then open the linked source documents for detail.

## Current canonical baseline
- Repository: `CK-NEXUS-AI/ck-nexus`
- Main SHA: `4d1366cef3cbdd18aa174bdf67308567635c750a`
- Main tree: `57adfe86cd6d9bdbca5c97d336cb733df2308ae5`
- Current operations branch: feat/agnes-persistent-ops-memory-20261110 (local-only; not pushed or merged).
- Agnes bounded parallel implementation commits: 6fd0b39690ff92bfeb26789bcd145578cbb0b727 and 501f170be424c0352b5b76b12fb37b49b3a51bb4; base 4d1366cef3cbdd18aa174bdf67308567635c750a.
- Reliability-guard commit `873af83ba55a97075ba00c0a9f34a1ff30865a6d` is local-only and unpushed: durable TaskStore idempotency, cooperative request cancellation, and process-wide worker cap 2. Focused regression 151 passed, 1 known pytest configuration warning; Ruff, compileall and diff checks passed.
- MCP adapter tests are blocked at collection because the Termux Python environment lacks declared dependency `mcp>=1.13,<2`; do not claim MCP adapter integration verified.
- Cancellation is cooperative; non-cooperative running threads cannot be forcibly stopped. Global concurrency is per process, not cross-process.
- Separate PR #364 branch head: `954c5e6c64b1f0f678fa1192476c63c7349e85d2`; PR OPEN / REVIEW_REQUIRED / BLOCKED; latest inspected required checks passed; Cubic review pending; do not merge.

## Non-negotiable constraints
- Core/L3 is sole authority; n8n is workflow plane only; external tools are authority_level=NONE.
- NO EVIDENCE -> NO DONE.
- DESIGNED != IMPLEMENTED != EXECUTED != VERIFIED != PRODUCTION.
- No secrets in files, commands, logs, task payloads or evidence.
- Do not weaken release gates or claim production readiness.
- Work in isolated branches/worktrees; no force-push or automatic merge.
- No VPS access was performed.

## Current product facts
- Existing agents: Architect, Scout, Security, Verifier prompts; AI Expert Team Director, Engineer, Guardian, Analyst, Researcher, Designer, Connector.
- TeamDirector now uses the existing ParallelExecutor for bounded dependency waves, with sync/async APIs, isolated worker snapshots, deterministic result integration, fail-closed statuses, and per-agent locks across concurrent requests. Remaining WQ-005 gaps: idempotency/duplicate-task prevention, cooperative cancellation/worker lifecycle, and a global concurrency budget. A Python thread already running is not forcibly stopped by asyncio timeout/cancellation.
- Existing SQLite task queue and MCP adapter are present and have local tests; live deployment was not verified.
- SharedKnowledge persistence is optional and TeamDirector defaults to no persistence. SemanticMemory and UnifiedMemoryStore are in-memory; personal memory is consent/TTL-gated but in-memory.
- Extend existing modules; do not create duplicate agent or authority systems.

## Release facts
- Production remains NO-GO.
- Current evidence JSON source SHAs differ from main 4d1366c; Q11 is BLOCKED, Q12 PASS is historical/stale, Q13/Q15/Q16 image are PASS_CANDIDATE but stale, Q14 PASS is stale, Q16 license PASS is stale. Q10 whole gate is not established by the inspected file.
- RELEASE_STATUS.md contains an older main SHA and needs controlled reconciliation.

## Next actions
1. Provision the declared MCP dependency in an isolated test environment and run the new MCP idempotency adapter tests; independently review WQ-005 reliability changes. Keep this local branch unpushed until an explicit push decision.
2. Finish PR #364 Cubic review; keep it unmerged.
3. Recalculate the exact current candidate runtime subject and rebaseline Q10–Q16.
4. Reconcile stale RELEASE_STATUS and closure documentation using verified evidence only.
5. Design and test durable Unified Memory storage with consent, tenant isolation, classification, retention and deletion.
6. Verify task queue and MCP service in a permitted non-production environment before any deployment claim.
7. Complete developer onboarding, evidence bundle and commercial packaging.
