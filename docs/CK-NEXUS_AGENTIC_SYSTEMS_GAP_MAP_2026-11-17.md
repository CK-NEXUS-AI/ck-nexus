# CK-NEXUS Agentic Systems Gap Map
**Research date:** 2026-11-17  
**Repository baseline:** 40650ddf4dc92588c53d340725f0988c0b1880d3 (feat/ck-nexus-test-portal)

> Research and implementation-planning artifact only. This is not a production-readiness attestation. Design, code presence, API-key presence, or a passing unit test does not prove a live capability.

## 1. Executive finding

CK-NEXUS already has extensive architecture and implementation plans: canonical runtime, unified architecture, AGNES execution-kernel security baseline, credential broker/provider cutover, skill nervous system, cognitive runtime, distributed idempotency and Q10-Q16 closure contracts. The main gap is not a lack of ideas. It is closing the gap between design, implementation, live infrastructure, independent verification and one controlled release.

Preserve the existing authority chain:

Human Principal -> Agent Identity -> Capability Lease -> Policy/Reversibility -> Approval -> Credential Broker -> Deny-by-default Sandbox -> Execution Journal -> Executor -> Independent Effect Verification -> Evidence.

Do not create a second authority plane inside n8n, an agent framework, an MCP server or a model provider.

### Evidence snapshot from current project context and VPS checks in this session

| Area | Observed | Status |
|---|---|---|
| Public Chat Portal | GitHub Pages returned HTTP 200; chat-config.json returned HTTP 200 | Public UI reachable |
| Public Chat API | Authenticated chat status HTTP 200; ready=true; provider openrouter; model openrouter/free | One provider path live, not full-system proof |
| Provider router | Authenticated provider status HTTP 200; free_only=true; OpenRouter and Gemini registered | Gemini previously returned HTTP 503 on generation; registration is not inference proof |
| n8n VPS service | /healthz and /healthz/readiness HTTP 200; loopback port 5678 listening | Workflow/credential APIs returned 401 without auth; inventory not verified |
| Chat tunnel | Quick Tunnel URL present in service logs | Temporary URL, not stable production edge |
| PR #370 | Head 40650ddf...; Pages build/deploy passed | CodeQL, attack-regression, preflight and test checks failed; keep Draft/unmerged |
| AGNES | Phase-1 kernel and guards documented | Local/Docker sandbox executors and production-safe distributed idempotency explicitly incomplete in phase baseline |
| Q10-Q16 | Closure contract and runbooks exist | Not collectively verified on one current immutable release subject; Production remains NO-GO |

**Architecture drift:** R14 says n8n is retired from active runtime, but an n8n service is still running on the VPS. Decide whether it is an approved subordinate automation plane or retire it through a reviewed migration. Do not let it become a second policy authority.

## 2. Systems to finish

### P0 — required before a governed end-to-end execution test

| System | Required work | Implementation pattern | Acceptance evidence |
|---|---|---|---|
| 1. Canonical Control Plane | One API for identity, leases, policy, approval, budget, kill switches and execution state | Keep CK-NEXUS as sole authority; version contracts; evaluate OPA/Rego only as a policy decision engine, not a second authority | Allow/deny tests, decision IDs, fail-closed behavior, cross-service contract tests |
| 2. Agent Identity & Capability Leases | Unique identity per human, agent, tenant, worker and tool; short-lived scoped leases | Keep current contracts; evaluate SPIFFE/SPIRE for cryptographic workload identities when multi-host workers are ready | Provenance, expiry/revocation, audience binding, least privilege, impersonation tests |
| 3. Execution Sandbox | Real isolated executor for AGNES skills and code tasks | Prototype Docker Sandboxes microVM first; compare gVisor/Firecracker/E2B/Daytona only after threat and cost review. No host Docker socket; strict egress; explicit workspace mounts | Host escape, network deny, credential isolation, CPU/RAM/PID limits, clean teardown |
| 4. Sticky Approval & Human Gate | Approval bound to exact action, inputs, actor, target, risk, policy, executor and credential scopes | Preserve immutable execution manifest and fingerprint; any material change invalidates approval | Replay/change-input/expired-approval tests and audit trail |
| 5. Credential Broker | Durable encrypted secret storage, per-consumer leases, rotation, revocation and audit | Keep secrets out of prompts, workflow payloads and agent memory; evaluate OpenBao or Vault; short TTL dynamic credentials | Rotation/revocation tests; no secret in logs/status/evidence; broker outage fails closed |
| 6. MCP / Tool Governance | Approved tool registry, schema/version pinning, server identity, per-tool permissions and outbound policy | Follow MCP authorization guidance; hash full tool definitions; quarantine new servers/skills; no token passthrough; isolate credentials per server | Tool poisoning, confused deputy, SSRF, replay, cross-tenant and schema-change tests |
| 7. Durable Execution & Idempotency | Recoverable long-running jobs, retries, cancellation, resume and duplicate suppression | Complete Redis/PostgreSQL idempotency; compare Temporal durable workflows with LangGraph checkpointing; select one orchestration owner | Kill/restart recovery, duplicate submission, timeout, cancellation, retry and replay tests |
| 8. Independent Verification & Evidence | Verify real side effects separately from agent claims; immutable evidence bundles | Keep Evidence Engine separate from planner/executor; bind evidence to run ID, subject SHA, manifest hash, policy version, tool/provider and timestamps | Negative tests prove EXECUTED is not VERIFIED; tamper detection and signed evidence |

### P1 — required for reliable daily operations

| System | Required work | Implementation pattern | Acceptance evidence |
|---|---|---|---|
| 9. Provider Gateway | Catalog, key ownership, free/paid classification, model capability, quotas, circuit breakers and budgets | Retain current router first; evaluate LiteLLM only for measured gaps. Track provider/model/region/plan and last successful inference. No paid fallback | Live inference per provider; forced outage/fallback; zero-cost proof; usage/cost record |
| 10. Memory & Knowledge | Thread checkpoints, long-term facts, project knowledge, provenance, retention and deletion | Separate episodic run history from durable project memory; PostgreSQL metadata plus vector/hybrid search only when justified; evaluate LangGraph stores and Qdrant | Tenant isolation, source citations, poisoned-memory tests, retention/deletion and restore |
| 11. Observability & Alerting | One trace across UI, API, agent, tool, provider, workflow and verifier | OpenTelemetry trace context; record tool calls, model, latency, token usage, retry, policy decision and evidence ID; evaluate Langfuse UI | Failure-injection alerts reach operator; run reconstruction; secrets redacted |
| 12. Evaluation & Red Team | Golden tasks, policy regression, prompt injection, tool abuse, reliability and quality evaluation | Deterministic checks first; human review and model judges are secondary signals | Versioned datasets, thresholds, regression history and reproducible evidence |
| 13. Workflow/Automation Plane | Choose one supported engine and define its boundary | If n8n is retained, it submits typed task IDs/allowlisted operations to CK-NEXUS; no arbitrary shell or self-approval. Otherwise retire cleanly | Authenticated workflow inventory, webhook auth, audit, idempotency, dangerous-node review |
| 14. Operator Control Center | UI for service health, agents, leases, approvals, queues, providers, spend, alerts and evidence | Read-only status APIs first; all mutations use governed APIs and show approval state | Browser E2E, role separation, stale-data indicators, kill-switch proof |
| 15. Stable Edge & Network | Stable HTTPS, TLS, rate limits, origin controls and private admin paths | Replace Quick Tunnel with owned named tunnel/domain or stable authenticated edge; keep admin endpoints private | DNS/TLS monitoring, ingress, CORS and network tests |
| 16. Backup/Restore & DR | Back up database, evidence/object store, configuration metadata and agent memory | Complete Q13 with isolated restore target; define RPO/RTO, encryption, retention and restore drills | Verified restore with counts and hashes; never overwrite live DB destructively |
| 17. Clean Install & Release | Reproducible runtime, pinned dependencies, migrations, health checks and rollback | Complete Q15 on a clean supported VM; bind all evidence to one immutable release SHA | Clean-machine install, migrations, smoke, rollback and exact-subject evidence |

### P2 — after P0/P1

- Multi-tenant organization/workspace administration, isolation and quotas.
- Agent-to-agent interoperability (evaluate A2A and MCP boundaries); all messages remain untrusted until CK-NEXUS validates them.
- Skill marketplace/discovery with quarantine, signatures, license and malware checks; never auto-install discovered skills.
- Local model runtime and hardware-aware scheduling after measuring VPS/Termux limits.
- Business OS connectors (CRM, email, calendar, billing, sales, analytics) with scoped OAuth and explicit send/write approvals.
- Self-improvement pipeline with proposal, tests, sandbox, independent review, canary and rollback; no automatic merge or production promotion.

## 3. Useful candidate projects

These are candidates, not an instruction to install all of them. Avoid framework sprawl.

| Candidate | Potential role | Recommendation |
|---|---|---|
| Docker Sandboxes | MicroVM isolation, network policies, credential proxy, per-agent environment | High-priority sandbox prototype; verify account/billing and host compatibility first |
| Open Policy Agent | Policy-as-code decision service | Prototype only if current in-process policy has duplicated rules or cross-service needs |
| SPIFFE/SPIRE | Workload identity and short-lived cryptographic identity | Later-stage option for multiple hosts/workers |
| LiteLLM | Unified model gateway, virtual keys, budgets, rate limits, routing/fallback | Benchmark against current router; do not replace without evidence |
| LangGraph | Stateful workflows, checkpointing, human-in-the-loop and resume | Useful for selected long-running cognitive flows; CK-NEXUS remains authority |
| Temporal | Durable orchestration across restarts and long-running jobs | Compare with existing orchestration before choosing one workflow owner |
| Langfuse | Trace inspection, prompt/skill versioning and evaluations | Good candidate after data redaction/retention design |
| Qdrant | Vector search and snapshots for knowledge retrieval | Add only when retrieval benchmark justifies it |
| OpenBao / Vault | Encrypted secret storage, leases and revocation | Required capability; select one after deployment/maintenance review |
| OpenTelemetry | Common trace/metric/log instrumentation | Adopt as telemetry contract, regardless of backend |
| n8n | Business automation and connectors | Keep subordinate to CK-NEXUS or retire; never grant independent authority |

## 4. Repeatable build recipes

### A. Governed task execution
1. Accept typed task request: task_id, tenant_id, actor_id, capability_id and idempotency key.
2. Resolve agent/workload identity; verify token audience, expiry and scope.
3. Resolve capability and risk; reject unknown tools and malformed inputs.
4. Ask Policy Kernel for a decision; record policy version and decision ID.
5. Require approval for high-impact/irreversible actions; bind approval to exact manifest hash.
6. Ask Credential Broker for a short-lived consumer-bound lease; never send raw secrets to the model.
7. Create isolated sandbox with explicit filesystem and network allowlists.
8. Execute only through registered executor; enforce time, memory, CPU, PID and output limits.
9. Independently verify the external effect, not just process exit code or agent statement.
10. Redact, hash, sign and append evidence; return separate planned/executed/verified/promoted states.

### B. Free-first provider onboarding
1. Record provider, model, region, account tier, free quota, expiry/limits and official pricing URL.
2. Check key presence without displaying/copying its value.
3. Probe model-list/metadata endpoint (read-only).
4. Run a small inference test only when quota/cost is known and explicitly approved.
5. Record response sentinel, HTTP status, model, latency and usage; model-list HTTP 200 is not inference proof.
6. Route only after live inference and zero-cost eligibility are verified.
7. Test timeout, retry, circuit breaker and fallback. Paid fallback remains disabled unless explicitly authorized.

### C. MCP server / skill onboarding
1. Discover only; do not install.
2. Record source owner, repository, immutable version/commit, license, checksum and provenance.
3. Inspect every tool schema, permissions, filesystem access and network destinations.
4. Scan package/scripts and dependencies; quarantine until reviewed.
5. Register unique server identity and per-server credential scopes.
6. Pin schema hashes; changes require review and regression tests.
7. Test prompt injection, tool poisoning, confused deputy, SSRF, replay and cross-tenant access.
8. Activate only through CK-NEXUS policy and explicit approval.

### D. Production evidence and release
1. Freeze immutable commit, tree and deployment-subject digest.
2. Run frozen dependency install, secret scan, SAST, dependency audit, security regression and full tests.
3. Run live staging tests for providers, sandbox, database, Redis, workflow engine and connectors.
4. Inject failures; verify alert delivery, recovery, rollback and evidence integrity.
5. Perform isolated backup/restore and clean-machine install.
6. Collect Q10-Q16 evidence against that same subject.
7. Independent review; then owner approval for production promotion.
8. CI pass, deployed UI, running service or API-key presence alone never proves full readiness.

## 5. Recommended implementation order

1. Baseline/drift: inventory processes, ports, repo SHA, worktrees, workflows, credential names (never values), services and public endpoints. Resolve n8n-retirement contradiction and choose one canonical runtime.
2. P0 execution path: identity -> lease -> policy -> approval -> credential -> sandbox -> executor -> verifier -> evidence. Complete real sandbox and distributed idempotency.
3. Provider and MCP: finish broker/router and approved tool registry with live tests and no paid fallback.
4. Durability: PostgreSQL/Redis, checkpointed jobs, outbox, replay and restart recovery.
5. Operations: telemetry, alert delivery, control-center UI, stable HTTPS, backup/restore and clean-machine deployment.
6. Release closure: Q10-Q16 against one exact candidate; fix CI failures before promotion.
7. Expansion: additional agents, skills, integrations and business modules only after the control path passes.

## 6. Non-negotiable acceptance rules

- DESIGNED != IMPLEMENTED != EXECUTED != VERIFIED != PRODUCTION.
- CONNECTED != AUTHORIZED; AUTHORIZED != EXECUTED; EXECUTED != VERIFIED.
- No access -> no claim. No evidence -> no done.
- Model, agent, workflow engine, MCP server and provider are never policy authorities.
- No secrets in Git, chat prompts, logs, memory, evidence bundles or browser storage.
- Deny by default; least privilege; short-lived credentials; kill switches.
- No arbitrary shell through webhook payloads.
- No paid provider fallback, credit spend, external messages, merge or production deploy without relevant approval.
- All release evidence must bind to one immutable subject.

## 7. Source references

### Official implementation and security documentation
1. Docker Sandboxes isolation: https://docs.docker.com/ai/sandboxes/security/isolation/
2. Docker Sandboxes quickstart: https://docs.docker.com/ai/sandboxes/get-started/
3. Docker Agentic Platform (experimental; review billing/maturity): https://docs.docker.com/agentic-platform/
4. OPA policy-as-code: https://www.openpolicyagent.org/docs
5. SPIFFE/SPIRE architecture: https://spiffe.io/docs/latest/spire-about/spire-concepts/
6. SPIFFE SVIDs: https://spiffe.io/docs/latest/deploying/svids/
7. MCP authorization security: https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations
8. OWASP MCP Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html
9. OWASP Top 10 for Agentic Applications: https://genai.owasp.org/2025/12/09/owasp-genai-security-project-releases-top-10-risks-and-mitigations-for-agentic-ai-security/
10. OWASP GenAI LLM Top 10 2026: https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/
11. LiteLLM gateway architecture: https://docs.litellm.ai/docs/proxy/architecture
12. LiteLLM retries/fallbacks: https://docs.litellm.ai/docs/router/learn/reliability
13. LangGraph persistence: https://docs.langchain.com/oss/python/langgraph/persistence
14. Langfuse prompt/skill management: https://langfuse.com/docs/prompt-and-skill-management/overview
15. n8n security audit: https://docs.n8n.io/hosting/securing/security-audit/
16. Qdrant snapshots: https://qdrant.tech/documentation/operations/snapshots/

### Existing CK-NEXUS design/gate documents (research baseline branch)
- docs/ARCHITECTURE.md
- docs/CANONICAL_RUNTIME.md
- docs/CK_NEXUS_UNIFIED_ARCHITECTURE.md
- docs/AGNES_EXECUTION_KERNEL_PHASE1_SECURITY_BASELINE.md
- docs/PRODUCTION_CLOSURE_Q10_Q12_RUNBOOK.md
- docs/Q10_Q16_CLOSURE_CONTRACT.md
- docs/R7_CREDENTIAL_BROKER_PROVIDER_CUTOVER.md
- docs/R13_AGNES_SKILL_NERVOUS_SYSTEM.md
- docs/R14_COGNITIVE_BRAIN_RUNTIME.md
- docs/R17_DISTRIBUTED_IDEMPOTENCY_RUNTIME.md
- docs/CK-NEXUS-FREE-API-PROVIDERS.md

**Disposition:** Research saved as a development-planning artifact. No project is approved for blind installation. No production gate is waived. Next target: P0 governed execution path plus exact-subject Q10-Q16 closure.
