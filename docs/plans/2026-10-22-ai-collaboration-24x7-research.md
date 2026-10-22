# CK-NEXUS AI Collaboration 24/7 — Research and Design Notes

Date: 2026-10-22
Status: Research/design proposal; not a production authorization or deployment record.
Goal: Reuse existing CK-NEXUS components and free/local capabilities first, with durable 24/7 execution and governed self-improvement through L6.

## Design principles

1. Reuse-first: keep the existing Control Plane, SQLite task store, MCP, execution kernel, sandbox, verification, evidence, and watchdog. Do not install a second orchestrator unless a documented gap justifies it.
2. Event-driven, not infinite chat: wake agents for queued tasks, failures, scheduled health checks, quota events, and approval events. Bound each run by time, retries, token/API budget, and loop detection.
3. Durable state: persist task, owner, lease, checkpoint, inputs/outputs, provider, attempts, policy decision, test result, and evidence references. Recover expired leases after restart.
4. Model/provider routing: check configured auth and known pricing/quota before a call; prefer local/free eligible routes; never assume a CLI login or a free tier means unlimited/free usage. Add timeout, circuit breaker, retry budget, and provider fallback.
5. Safe engineering: use isolated worktree/sandbox; run targeted tests, lint, security checks, and diff review; promote only when all required gates pass. Keep rollback/evidence. Do not delete original sources or failed-test logs as cleanup.
6. Least privilege: agents receive only the tools/scopes needed for a task. Secrets stay in protected credential storage and never enter prompts, logs, or reports.
7. 24/7 is a service property: use systemd or an equivalent supervisor, health checks, bounded restart policy, persistent queue, log rotation, disk thresholds, and a kill switch. The chat UI itself is not the 24/7 worker.

## Reference ideas to evaluate (not automatic dependencies)

- LangGraph: explicit state graphs, checkpoints, resumable workflows, and human approval interruptions.
- CrewAI: role/task-based teams and flow-based coordination.
- Temporal: durable execution, retries, and long-running workflow recovery.
- OpenWOP: an emerging open workflow protocol for pause/approve/resume, event trails, replay, and interoperability. Evaluate maturity before production adoption; do not add solely because it is new.
- MCP: tool access interface; reuse CK-NEXUS MCP.
- A2A: cross-agent delegation/communication when independently hosted agents actually need it.

Primary references:
- LangGraph: https://github.com/langchain-ai/langgraph
- CrewAI: https://github.com/crewAIInc/crewAI
- Temporal docs: https://docs.temporal.io/
- OpenWOP: https://github.com/openwop/openwop
- MCP: https://modelcontextprotocol.io/
- A2A: https://a2a-protocol.org/
- Gmail API scopes: https://developers.google.com/workspace/gmail/api/auth/scopes
- Gmail API quotas: https://developers.google.com/workspace/gmail/api/reference/quota
- Gmail server-side OAuth: https://developers.google.com/workspace/gmail/api/auth/web-server

## Suggested team roles

- Supervisor/Dispatcher: queue routing, lease management, policy enforcement, bounded concurrency.
- Researcher: source-backed research and proposal drafting; cannot directly promote changes.
- Architect: turns validated findings into small, testable plans.
- Developer: implements changes only in isolated workspace.
- Test Engineer: runs tests and records raw results independently of the implementer.
- Security Reviewer: checks secrets, permissions, dependency changes, network exposure, and destructive operations.
- Evidence/Release Agent: creates manifests, hashes, change summaries, and promotion/rollback records.
- Human Owner: controls OAuth grants, policy expansion, billing, external email, production deployment, and high-impact/destructive actions.

## Approval authority and daily quota proposal

Treat the requested 20/day as a CK-NEXUS internal policy cap, not a Google API quota. Initially count each distinct privileged change/connection request as one unit, including: connecting a new external service/account, creating a new integration/tool, requesting additional OAuth scopes, and promoting a change to production. Deduplicate retries of the same idempotent request; retries must not create a second side effect. Keep separate counters for API usage, model spend, and privileged changes.

- Tier A (pre-authorized): read-only health/status, local tests, report generation, checkpointing, evidence collection, and sandbox-only changes within an approved task.
- Tier B (within approved policy and daily cap): create a draft integration, create a sandbox tool, or prepare a change proposal. Require tests, security review, audit entry, and an explicit promotion rule.
- Tier C (human confirmation required): OAuth consent/grant, enabling broader Gmail scopes, external email sending, paid service activation, production deploy, destructive data changes, secret rotation, policy/limit increase, and disabling security controls.
- Hard stop: when 20/20 units are consumed, queue further privileged operations and notify the owner. Do not bypass the cap through another agent, provider, account, or retry.
- Expansion: owner-approved policy change must record old/new cap, scope, approver, timestamp, rationale, expiry/review date, and tests. Raising the cap does not waive provider quotas, pricing checks, OAuth verification, or human-only gates.

The AI may act as a policy executor for decisions the owner has pre-authorized. It must not impersonate the owner, bypass MFA/OAuth consent, click through legal/billing approvals without consent, or grant itself new permissions. Actual Google OAuth consent remains an account-owner/admin action where Google requires it.

## Gmail integration policy

1. Start with the narrowest OAuth scope and one clearly defined purpose. Prefer metadata/labels or draft preparation where sufficient; do not request `mail.google.com` or broad restricted scopes unless there is a justified requirement and the necessary verification/security review is completed.
2. Separate reading, drafting, and sending permissions. Default to draft-only; require explicit approval for external sends until a narrow, tested sending policy is separately authorized.
3. Store OAuth refresh tokens only in protected secret storage, restrict access to the runtime service account, redact tokens and message bodies from logs, and support revocation.
4. Apply allowlisted recipients/domains, message templates, duplicate/idempotency protection, rate limits, audit logs, and a kill switch.
5. Do not use Gmail as an unrestricted channel for agents to converse continuously. Use the internal queue/event log; email only for owner notifications and approved business workflows.
6. Respect Google quotas and billing terms. The internal 20-action cap is not the Gmail API's quota and does not guarantee free usage.

## L1–L6 acceptance gates

- L1 Infrastructure: services supervised, health checks, disk/log limits, restart and recovery tests.
- L2 Tool Execution: inventory of tools/auth/scopes, least privilege, timeouts, audit logs, deny-by-default for unknown tools.
- L3 AI Agent: verified live-call test per provider, explicit cost/quota classification, timeout and fallback tests.
- L4 Multi-Agent Orchestration: durable queue, leases, checkpoint/resume, deduplication, bounded concurrency, no infinite loops.
- L5 Autonomous Engineering: isolated changes, independent tests/review, security gate, evidence, rollback drill.
- L6 Governed Self-Improvement: policy versioning, approval authority, quota enforcement, immutable audit trail, safe promotion/rollback, failure injection, and a sustained 24-hour soak test with no uncontrolled spend or unauthorized side effects.

## Deployment constraints and next steps

- Existing repository contains many user changes; preserve them. Do not reset/clean or overwrite unrelated files.
- Previous environment observation: root filesystem about 91% used with roughly 3.9 GiB free. Recheck before installing dependencies or running soak tests.
- Runtime MCP is reported at `/opt/cknexus-mcp` under a dedicated service user while source repo is `/root/ck-nexus`; design a narrow deployment/artifact boundary instead of granting broad `/root` access.
- Before claiming 24/7, verify the actual worker process, systemd unit, journal heartbeat, queue progress, restart recovery, budget cap, and kill switch on the VPS.
- First implementation slice should be a policy/quota ledger and read-only dry-run report, then tests, then a sandbox worker. Do not enable Gmail send or production promotion by default.
