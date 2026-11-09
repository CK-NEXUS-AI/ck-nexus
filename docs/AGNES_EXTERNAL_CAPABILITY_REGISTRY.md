# AGNES External Capability Registry

**Review date:** 2026-11-09
**Repository baseline:** main at 4d1366cef3cbdd18aa174bdf67308567635c750a
**Canonical inventory:** [config/capability_catalog.json](../config/capability_catalog.json)
**Architecture:** [Unified Capability Fabric V1](architecture/UNIFIED_CAPABILITY_FABRIC_V1.md)

## 1. Source of truth and authority

The reviewed main branch does not contain the legacy paths config/agnes_external_capability_registry.json or docs/AGNES_EXTERNAL_CAPABILITY_REGISTRY.md. The canonical machine-readable inventory is config/capability_catalog.json. This document restores the requested human-readable entry point without creating a second JSON source of truth.

The catalog is descriptive only. It does not grant credentials, execution rights, approvals or authority. CK-NEXUS Core / L3 remains the sole authority for state, memory policy, permissions, execution grants, evidence and release gates. Every external provider, tool, plugin, connector, skill, workflow engine, framework, parser and observer must have authority_scope=NONE.

## 2. Independent verification states

These flags are independent and must never be collapsed into a generic "available" or "integrated" status.

| Field | Meaning | Does not prove |
|---|---|---|
| discovered | Candidate or tool namespace was located. | Trust, safety, installation or availability. |
| available_in_chat_session | Tool surface is exposed in this ChatGPT session. | Account authentication, permission to act or CK-NEXUS availability. |
| online_verified | Authoritative upstream source, official docs, release or package metadata checked on the review date. | Works in CK-NEXUS. |
| not_connected | No live authenticated connection to the external service was verified. | No adapter/source-code integration exists. |
| not_integrated | No CK-NEXUS adapter/runtime wiring was demonstrated. | The external service is not connected; a live connection may exist independently. |
| runtime_verified | Pinned candidate was exercised through CK-NEXUS runtime and evidence captured. | A future version or different deployment subject. |

The existing status field remains the installation/inventory state (present, partial, discovery_only, not_installed or blocked). New candidates remain discovery_only. Every non-core artifact must declare the exact six boolean verification_state fields; CK-NEXUS Core is the only exception. The loader rejects missing, extra or non-boolean fields and impossible runtime_verified combinations. These flags are read-only research metadata; they do not activate, authorize, connect or execute anything.

The nine discovery-only candidates below have discovered=true, available_in_chat_session=false, online_verified=true, not_connected=true, not_integrated=true, runtime_verified=false and authority_scope=NONE. The OpenAI Agents SDK is recorded separately as an existing partial integration: source/dependency wiring is present, but no live external connection or CK-NEXUS runtime verification was performed.

## 3. Candidates reviewed

| Candidate | Version/date | License | Compatibility and footprint | Decision |
|---|---|---|---|---|
| [Agent Skills specification](https://github.com/agentskills/agentskills) | Living spec; no GitHub Releases observed 2026-11-09 | Apache-2.0 | Format only; no runtime dependency. Skills may bundle scripts. | Use as metadata/conformance reference only; pin commits and validate; no auto-install. |
| [AgentClash](https://github.com/agentclash/agentclash) | v2.3.0 (2026-11-08) | MIT | Go module declares 1.26.8; self-host guide lists Go 1.25+, Node 22, pnpm, Docker, PostgreSQL, Redis and Temporal. Full stack; footprint not measured. | Useful real-agent replay/regression candidate; compare on an isolated worker against Promptfoo/Inspect AI; no hosted account or VPS install. |
| [Letta Code](https://github.com/letta-ai/letta-code) | v0.34.46 (2026-11-09) | Apache-2.0 | Node 22.23.4/24.22.1/26.12.1; Bun >=1.3.2; optional Python 3.9+; MCP SDK, node-pty, sharp, OpenAI/Letta SDKs. Package size not measured. | High-value memory/skills harness, but default permission mode is unrestricted and agents self-modify memory/skills/prompts; discovery-only, no VPS install or account link. |
| [Promptfoo](https://github.com/promptfoo/promptfoo) | 0.125.1 (2026-10-25) | MIT | Node.js >=22.22.0; 74 direct runtime dependencies and 52 dev dependencies; VPS Node 24.22.1 meets engine. | Highest-priority candidate for isolated CI evals and LLM/agent red-team tests. |
| [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) | 0.3.288 (2026-11-07; PyPI Trusted Publishing provenance observed) | MIT | Python >=3.11; broad dependency surface including cloud SDKs, FastAPI, numpy, fsspec/s3fs, textual and tiktoken. | Optional separate CI benchmark worker; not production dependency or VPS co-install. |
| [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) | 0.0.84 (2026-10-31) | Apache-2.0 | Node.js >=18; release pins Playwright 1.65.0-alpha-2026-10-30 plus browser engines. | Evaluate only if existing CK-NEXUS browser adapter has a proven coverage gap. |
| [Official MCP Registry](https://registry.modelcontextprotocol.io/) | v1.8.8 (2026-11-06) | MIT legacy contributions; Apache-2.0 new code/spec contributions; CC-BY-4.0 docs during transition | Hosted read-only REST API; no local dependency. Self-hosting requires Go, Docker/ko, PostgreSQL and operations. | Add as read-only discovery metadata source only; registry listing is not a security approval. |
| [OpenSandbox](https://github.com/opensandbox-group/OpenSandbox) | 1.2.0 stable (2026-10-27); 1.2.1-rc.1 pre-release (2026-11-04) | Apache-2.0 | Python >=3.10; Docker or Kubernetes; 19 direct server dependencies plus controllers/ingress/runtime components. VPS has Docker but lacks Kubernetes and secure runtimes. | Strong future candidate for a separate sandbox worker; do not install on the current VPS. |
| [Langfuse](https://github.com/langfuse/langfuse) | v4.76.0 (2026-11-05) | MIT core; EE paths use separate license | Node 24, pnpm 12.16.1, Docker; PostgreSQL, Redis/Valkey, ClickHouse, S3/MinIO, web+worker; heavy multi-service stack. | v4.76 adds read-access audit events and Topics API/MCP. Keep discovery-only; separate infrastructure only after data/security review. |
| [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | 0.24.0 stable (2026-10-15); 0.24.0-alpha.6 pre-release (2026-11-03) | MIT | Python >=3.10; CK-NEXUS requires >=3.11; current lock resolves 0.19.3. | Existing partial integration; review lockfile upgrade separately; no runtime promotion. |

### 3.1 Agent Skills specification

Anthropic announced donation of the Agent Skills open standard to the Agentic AI Foundation under the Linux Foundation on 2026-10-22. Anthropic reports that more than 70 agent platforms, including ChatGPT, Cursor, GitHub Copilot and VS Code, have integrated the format. The repository is Apache-2.0 licensed. The specification defines a portable SKILL.md folder format, progressive disclosure, optional compatibility metadata and an experimental allowed-tools field. The latter is not a security boundary and support may vary by client. Platform-level format support does not prove that a particular skill bundle is installed in this ChatGPT session or that CK-NEXUS Runtime has integrated the loader.

No GitHub Releases were published at review time. Pin a reviewed commit SHA and file hashes rather than relying on a floating branch or assumed semantic version. A skill is procedure/content, not an identity, credential, permission grant or authority source.

### 3.2 Promptfoo

Promptfoo is a CLI/library for prompt, model, agent and RAG evaluation plus red-team testing. Official docs list 157 red-team plugins, including coding-agent probes for repository prompt injection, terminal-output injection, secret reads, sandbox escapes, verifier sabotage and delayed CI exfiltration. Some plugins are marked with a globe to indicate remote inference; the docs state these may send attack-generation context to Promptfoo's remote endpoint. OpenAI announced its planned acquisition of Promptfoo on 2026-03-09; the current upstream README says Promptfoo is now part of OpenAI and remains MIT-licensed.

Upstream package.json declares 74 direct runtime dependencies and 52 dev dependencies. The inspected VPS runs Node.js 24.22.1, which satisfies the documented >=22.22.0 engine, but Promptfoo was not found on PATH or in the global npm package list; no runtime test was performed. The Community plan is free and lists up to 10,000 red-team probes/month; model/provider calls and remote inference remain variable-cost and latency sources.

Security caveat: Promptfoo OSS does not provide a general sandbox for adversarial eval content. Configs, scripts, providers, datasets and pull-request content must be treated as untrusted code/data. Some remote-only plugins (including SSRF, BOLA/BFLA and indirect-prompt-injection tests) use Promptfoo-hosted generation. PROMPTFOO_DISABLE_REMOTE_GENERATION disables supported remote-generation fallbacks, but is not an egress firewall and does not disable all telemetry or configured provider traffic. Run in an isolated container/VM with least-privilege credentials and restricted egress; use synthetic/redacted fixtures. Its local web UI/MCP runs with invoking-user permissions and is not a security boundary; do not expose it to untrusted networks.

### 3.3 Inspect AI

Inspect AI provides task/dataset-based evaluations, solvers, scorers, model graders, tool-use tests, evaluation logs, tracing, retries, concurrency controls and time/message/token/cost limits. Docker sandbox support is available for tools explicitly routed through the sandbox interface. Provisioning a container alone does not isolate arbitrary evaluator code.

The latest 0.3.288 PyPI release (2026-11-07) includes Trusted Publishing provenance pointing to the official GitHub repository and release workflow; its wheel is 35.6 MB. Its broad Python dependency surface warrants a dedicated evaluation environment rather than the canonical CK-NEXUS application image. Model API usage and worker compute remain metered.

### 3.4 Microsoft Playwright MCP

Playwright MCP exposes browser navigation, accessibility snapshots, interaction, JavaScript evaluation, cookies/storage, optional network/devtools capabilities, tracing and test assertions. Release 0.0.84 adds named isolated browser contexts and configurable URL-parameter redaction.

The v0.0.84 package requires Node.js >=18 and pins Playwright 1.65.0-alpha-2026-10-30; the inspected VPS Node.js 24.22.1 satisfies the engine requirement, but the package was not found in PATH/global npm and no runtime test was performed.

The upstream README explicitly states that Playwright MCP is not a security boundary. Its browser_run_code_unsafe tool executes arbitrary JavaScript in the MCP server process and is explicitly described as RCE-equivalent; deny it at the client policy. allowed-origins defaults to allow all, and origin filters do not protect redirects or provide a security boundary. Browser tools can mutate authenticated websites and access session state. Use a separately sandboxed container with no host secrets/mounts, enforced egress controls, loopback binding, isolated non-persistent contexts and restricted workspace roots. Do not attach logged-in profiles, use --no-sandbox or enable unrestricted file access for untrusted pages. URL redaction is convenience, not a security control.

For coding-agent flows, upstream documentation recommends considering Playwright CLI plus Skills for lower schema/token overhead. MCP remains useful for persistent browser state, exploratory automation and self-healing test loops. CK-NEXUS already has browser-automation scaffolding; compare it before introducing a second browser control surface.

### 3.5 Official MCP Registry

The official registry is the canonical public metadata directory for MCP servers. It stores server names, versions, package locations and installation metadata; it does not host the packages or inspect their code. The latest repository release observed is v1.8.8 (2026-11-06). Public reads are unauthenticated; publishing requires namespace ownership verification through GitHub OAuth/OIDC or DNS/HTTP proof.

The API documentation still labels the service as preview and warns that breaking changes or data resets may occur. The repository's license is in transition: legacy contributions remain MIT where relicensing consent is absent, new code/spec contributions are Apache-2.0, and documentation is CC-BY-4.0. Check the applicable license per file.

The public security page lists five advisories, including moderate unauthenticated SSRF and stored XSS plus low-severity open redirect, OIDC token replay and OCI ownership-check issues. Release v1.8.8 mentions security patches promoted to production, but the release notes do not map every advisory to a specific fix. Verify the deployed commit and advisory status. Namespace verification is not code scanning; independently validate package signatures, hashes, dependencies, permissions and network egress. Treat every registry entry as discovered metadata, never as trusted code or permission to install.

### 3.6 OpenSandbox

OpenSandbox is an Agentic AI Foundation project that provides a unified API, multi-language SDKs and CLI for code execution, command execution, file operations and browser/desktop-capable sandboxes on Docker or Kubernetes. The repository is Apache-2.0. The latest stable release is signed 1.2.0 (2026-10-27); 1.2.1-rc.1 was signed on 2026-11-04 but is a pre-release and its release notes say SDK/CLI packages are held for the stable 1.2.1 bump. The official main branch was updated on 2026-11-09.

The server requires Python >=3.10 and declares 19 direct runtime dependencies, including Docker, FastAPI/Starlette, Kubernetes client, OpenTelemetry, PostgreSQL/Redis clients, gRPC and protobuf. A Kubernetes deployment requires Kubernetes >=1.21.1, Helm 3, kubectl, CRDs, controller, ingress gateway and optional fast-sandbox components. Note a release metadata mismatch: the release-1.2.0 server/pyproject still describes Kubernetes as planned while the current official docs/chart provide Kubernetes deployment instructions; pin and test the exact server/chart pair before choosing that mode. Docker mode is available, but multi-tenancy requires Kubernetes namespaces and is not supported in Docker mode.

Security must be configured rather than assumed: an empty server.api_key disables API authentication; the default runc runtime provides process-level cgroups only, while gVisor/Kata/Firecracker require explicit server-level configuration. The upstream network-isolation guide says sandbox Pods can reach other Pod IPs by default unless egress isolation is enforced. Use a platform-level deny.always policy or a CNI-level control. The current egress sidecar's NAT interception is incompatible with gVisor; use Kata or CNI policy if both strong isolation and egress filtering are required. Pin image digests and verify Cosign/provenance signatures. The security policy supports only the latest release and main branch.

The inspected VPS has Python 3.12.3 and an active Docker 29.1.3 daemon, but no kubectl, runsc, kata-runtime, firecracker, opensandbox-server or installed OpenSandbox Python packages. It has only 2.2 GiB free disk and about 438 MiB RAM available. It is therefore not a suitable installation target. Upstream secure-runtime startup-overhead figures (gVisor 10-50 ms/50 MB, Kata QEMU ~500 ms/20-50 MB, Firecracker ~125 ms/5 MB) are vendor estimates, not CK-NEXUS benchmarks. Self-hosting has no per-request SaaS price stated, but adds compute, storage, cluster and operations costs.

Decision: keep discovery-only. Compare it against CK-NEXUS's existing Linux namespace/cgroup sandbox and sandbox_executor on a separate worker with a fixed conformance and isolation matrix. Do not deploy it on the current VPS or give it authority.


### 3.7 OpenAI Agents SDK — existing partial integration

OpenAI's Python Agents SDK is already declared in `pyproject.toml` (`openai-agents[sqlalchemy]>=0.19,<1`) and wired through `creator_app/openai_brain.py` and `creator_app/runtime.py`. The current `uv.lock` resolves version 0.19.3. Upstream PyPI lists 0.24.0 as the latest stable release (2026-10-15) with Trusted Publishing provenance; GitHub lists a signed 0.24.0-alpha.6 pre-release (2026-11-03). The upstream package is MIT licensed and supports Python >=3.10; CK-NEXUS requires Python >=3.11. The 0.24.0 wheel is 1.2 MB and source distribution 7.0 MB. The current 0.19.3 lock resolves `griffelib`, `mcp`, `openai`, `pydantic`, `requests`, `typing-extensions` and `websockets`; the SQLAlchemy extra adds `asyncpg` and `sqlalchemy`.

Current source integration uses `OpenAIProvider` and `RunConfig`; the newer upstream sandbox-agent APIs expose Shell, Filesystem, Skills and Memory capabilities, but those newer capabilities have not been integrated or tested in CK-NEXUS. Model usage is billed at the provider's normal rates; tool/handoff calls and sandbox provisioning add latency and compute. No CK-NEXUS performance or runtime benchmark was performed.

The SDK runs tools in the host process unless a separate sandbox provider is configured. Function/MCP tools can exercise whatever privileges and credentials are passed to them. Keep API keys in the Credential Broker/runtime, not prompts; restrict tool schemas, filesystem mounts, egress, retention and trace payloads; require human approval for side effects. The SDK is a worker orchestration library, not an authority source or security boundary.

**Verification state:** discovered=true, available_in_chat_session=false, online_verified=true, not_connected=true, not_integrated=false, runtime_verified=false, authority_scope=NONE. The source/dependency integration is present, but no live provider connection or CK-NEXUS runtime execution was verified in this review. The lockfile is behind upstream stable; evaluate a dependency update in a separate, tested change rather than upgrading automatically.

### 3.8 AgentClash — agent evaluation and regression platform

AgentClash is a MIT-licensed open-source platform for real-task agent comparisons, replay, scorecards, multi-turn challenge packs, datasets, CI gates and security stress runs. The official GitHub repository published v2.3.0 on 2026-11-08 and had active commits on that date. Its SECURITY.md describes the project as pre-1.0 and says security fixes target latest main and the latest release. No independent third-party audit was established in the sources reviewed.

The npm CLI wrapper declares Node >=18 and ships platform-specific Go binaries; v2.3.0 release assets are approximately 4.9–5.6 MB compressed. The backend/runtime Go modules include Docker and Kubernetes clients, AWS SDK, Temporal, OpenTelemetry, PostgreSQL and Redis dependencies. The self-host guide lists Go >=1.25, Docker, Node 22, pnpm, psql and curl, while the current backend/runtime go.mod declares Go 1.26.8. The local stack starts PostgreSQL, Redis and Temporal, then builds/runs the API server and worker; the web app is separate. E2B or Kubernetes/Docker sandbox configuration and S3-compatible storage are additional production-shaped components.

The hosted site listed a Free plan with 25 eval runs/month and bring-your-own LLM key plus E2B sandbox token; Pro was listed at $49/month or $39/month billed annually on 2026-11-09. Self-hosting avoids the software subscription but adds infrastructure, storage and sandbox costs. Model calls, sandbox startup, repeated trials and concurrency drive latency/cost; use spend caps and time limits. No CK-NEXUS performance benchmark was performed.

Security caveats: the upstream policy specifically calls out sandbox escape, secret exposure, tenant isolation, authorization bypass and injection. Its docs describe network-disabled-by-default behavior, URL/CIDR checks in the http_request primitive, and workspace-scoped secret references. However, the local self-host starter is explicitly development mode: auth is stubbed, the sandbox provider is a no-op until configured, and a throwaway secrets key is generated. The repository docker-compose file publishes PostgreSQL, Redis and Temporal development ports with demo credentials; never expose those defaults. Real agent runs execute code in configured sandboxes and may use workspace credentials, so isolate the worker, restrict egress and use test-only credentials.

Decision: keep discovery-only. Compare its replay, failure taxonomy and CI regression gates with existing CK-NEXUS tests, Promptfoo and Inspect AI before considering a separate-worker prototype. Do not adopt its hosted control plane, connect an account, install its skills, or grant it authority.

Verification state: discovered=true, available_in_chat_session=false, online_verified=true, not_connected=true, not_integrated=true, runtime_verified=false, authority_scope=NONE.

### 3.9 Letta Code — stateful coding-agent harness

Letta Code v0.34.46 was released on 2026-11-09 under Apache-2.0. It is the current CLI/agent-harness source; the older letta-ai/letta server repository remains a separate project (v0.16.8, 2026-05-14) and its README points current CLI, App Server, channels and runtime development to letta-code. The registry keeps those two artifacts separate.

Letta Code provides a git-backed MemFS for agent memory, project/global/agent-scoped skills, subagents, hooks, MCP clients, schedules, messaging channels, remote computers and secrets. Its defining capability is also its main governance risk: agents can rewrite their own memory, skills, prompts and even the harness. The skill system supports executable scripts, not just static instructions.

The npm package requires Node 22.23.4, 24.22.1 or 26.12.1 and Bun >=1.3.2; an alternative Python installation requires Python >=3.9 and ships Node. Linux wheels require glibc 2.28+ (x86-64/ARM64); Alpine/musl is unsupported. The VPS Node 24.22.1 meets the engine constraint, but the letta binary and npm package were not present and no runtime test was performed. Dependencies include the MCP SDK, node-pty, sharp, OpenAI and Letta SDKs, cron-parser and WebSocket support; package size was not measured.

Permission modes include unrestricted, standard, acceptEdits and strict. Upstream docs state the interactive CLI defaults to unrestricted; strict must be selected explicitly to ask before every tool. Secrets are injected into shell commands and scrubbed from output, but remain available to the invoked process. Remote computers and cloud secrets require Letta sign-in. No root SECURITY.md or independent third-party audit evidence was found in the inspected repository.

Decision: keep discovery-only. If later evaluated, use a separate sandbox, strict permission mode, reviewed/pinned skills, test-only credentials and no production secrets. All memory changes must be proposals reviewed by CK-NEXUS Core; Letta Code must never become a second memory authority.

Verification state: discovered=true, available_in_chat_session=false, online_verified=true, not_connected=true, not_integrated=true, runtime_verified=false, authority_scope=NONE.

### 3.10 Langfuse — observability and audit metadata update

Langfuse v4.76.0 was released on 2026-11-05; the repository remained active with commits on 2026-11-08 and 2026-11-09. This release adds read-access audit events for trace, session and score reads, plus Topics summaries/assignments/rules through the public API, MCP and in-app agent. Langfuse has been part of ClickHouse since January 2026.

The root LICENSE makes code outside enterprise paths MIT; ee/ and other explicitly excluded enterprise paths use ee/LICENSE, and third-party components retain their own licenses. The monorepo requires Node 24 and pnpm 12.16.1. Self-hosting runs web/API and worker containers plus PostgreSQL, Redis/Valkey, ClickHouse and S3-compatible object storage; the optional AI Gateway adds another service. This is a heavy multi-service deployment, not a lightweight SDK. Cloud pricing was not verified in this pass; self-hosting still incurs storage, database, worker and compute costs.

Security distinction: Langfuse Cloud reports SOC 2 Type II, ISO 27001 and annual external penetration tests. Those Cloud attestations do not automatically apply to self-hosted deployments. The SECURITY.md recommends the latest release. The self-host compose file contains placeholder/default Postgres, ClickHouse, MinIO, SALT and ENCRYPTION_KEY values; replace them and restrict inbound ports. Most data services bind to localhost, while web, MinIO and optional AI Gateway ports need explicit firewall policy. The default telemetry setting is enabled, so review it against the data policy.

Permission/data scope is broad: SDK/OTel instrumentation can ingest prompts, completions, tool inputs/outputs, traces, observations, sessions and scores. Project-scoped API keys and RBAC gate reads; Topics is also exposed through API/MCP. Masking, retention, deletion and audit-log controls should be reviewed before any export. Event volume, sampling, retention and ClickHouse queries drive latency/storage; no CK-NEXUS benchmark was performed.

Decision: keep discovery-only. Compare its audit-log and data-minimization coverage with the existing OpenTelemetry and CK-NEXUS evidence pipeline before considering a separate deployment. Do not install it on the current constrained VPS and do not route policy, memory or authority through it.

Verification state: discovered=true, available_in_chat_session=false, online_verified=true, not_connected=true, not_integrated=true, runtime_verified=false, authority_scope=NONE.

## 4. ChatGPT session tool inventory (session-only)

These namespaces were exposed in the current ChatGPT tool catalog. This is a session-availability snapshot, not proof that each external account is authenticated or that CK-NEXUS can call these services.

| Area | Namespaces exposed | State |
|---|---|---|
| Repository/developer workflow | GitHub, Atlassian Rovo, Linear | available_in_chat_session=true; GitHub repository reads were exercised; Rovo and Linear were not invoked. |
| UI/design | Figma, Canva | available_in_chat_session=true; definitions surfaced; no design action/account access tested. |
| Browser/remote operations | TinyFish, Remote Desktop Commander | available_in_chat_session=true; TinyFish not invoked; device listing and read-only VPS checks succeeded through Remote Desktop Commander. |
| Build/deploy/data | Vercel, Replit, Lovable, Base44, Wix, Supabase, Neon, MongoDB Atlas | available_in_chat_session=true; no project modified, deployed, or account data read. |
| AI/agent/ML | Manus, Hugging Face, OpenAI Platform | available_in_chat_session=true; definitions surfaced; no model repository, agent task, or key-management action performed. |
| Knowledge/collaboration | Notion, Slack, Microsoft SharePoint, Gmail, Google Calendar, Granola, Airtable, Asana, monday.com, Soluvery | available_in_chat_session=true; no connected content was read or changed for this inventory. |
| Workflow/task automation | Automations, Reclaim.ai, Todoist, TickTick | available_in_chat_session=true; no task, schedule, or external workflow was created. |

All listed namespaces have discovered=true and available_in_chat_session=true. online_verified=true only for GitHub and Remote Desktop Commander because repository reads and read-only VPS checks succeeded; online_verified=false for every other listed namespace because no live service action was performed. For every listed namespace, not_connected=true and not_integrated=true relative to CK-NEXUS Connector Fabric/runtime, runtime_verified=false, and authority_scope=NONE. A ChatGPT connector exposed in this session does not make it a CK-NEXUS Runtime plugin.

The available Skills tool returned no installed skill bundles for this session; this does not prove that the Agent Skills format is unsupported by the platform and does not demonstrate any CK-NEXUS skill installation. Plugin-management functions exposed dependency and permission operations but no marketplace-wide plugin discovery/list operation; therefore this review does not claim a complete marketplace inventory.

## 4.1 Read-only VPS compatibility snapshot

Read-only check on 2026-11-09: Node.js v24.22.1, npm 11.19.1, Python 3.12.3 and Docker 29.1.3 (daemon responsive); RAM 1.9 GiB total with about 602 MiB available; root filesystem has 2.2 GiB free (95% used). kubectl, runsc, kata-runtime and firecracker are absent. Global npm packages and PATH entries include Codex CLI 0.162.1, Gemini CLI 0.63.0, OpenCode 1.18.35, n8n 2.45.5, AnyClaw 0.2.5, PaeanClaw 0.2.3 and Bailian CLI 2.5.1. Their package entries and binary paths were observed, but no CLI command, authentication, task execution or CK-NEXUS integration was tested; they remain discovered=true, available_in_chat_session=false, online_verified=false, not_connected=true, not_integrated=true, runtime_verified=false and authority_scope=NONE. Promptfoo, AgentClash, OpenSandbox server, Inspect AI and Letta Code were not found on PATH or in the global npm package list; pip show returned no package metadata for inspect-ai, opensandbox or promptfoo. This is an installation/path snapshot, not runtime verification. The low free disk/RAM and absence of secure runtimes make this VPS unsuitable for browser engines, large evaluation dependency trees or a multi-component sandbox platform; use separate CI/sandbox workers if later approved.

## 5. Existing CK-NEXUS baseline

- config/capability_catalog.json is canonical; the legacy external-registry JSON path was absent from reviewed main.
- The existing agnes-skills entry remains present; this review adds Agent Skills only as a discovery-only format reference. No community skill was installed.
- Promptfoo and Inspect AI complement existing tests/security gates; AgentClash adds agent replay/regression research; Letta Code adds a self-modifying memory/skills harness for governance comparison; Langfuse adds audit/observability research. All remain discovery-only and none replaces Q10–Q16 evidence or independent review.
- Playwright MCP is not considered installed because browser scaffolding exists or ChatGPT exposes TinyFish. Existing browser code must be assessed before another adapter is added.
- OpenSandbox is a separate-worker candidate only; compare it with the existing Linux namespace/cgroup sandbox and sandbox_executor before any replacement or integration.
- OpenAI Agents SDK is already a partial source/dependency integration; its lockfile is at 0.19.3 versus upstream stable 0.24.0. Review the upgrade separately; no live provider or runtime verification is claimed.
- Existing LangGraph, Letta Server, Letta Code, Langfuse, AgentClash and workflow candidates remain discovery-only; no competing orchestration, memory, observability or workflow plane is proposed.
- Official MCP Registry is a discovery metadata source, not a package scanner or trust authority; retain Open VSX/other aggregators as subregistries only after separate curation.

## 6. Next evaluation order

1. Prototype Promptfoo in isolated, non-production CI with synthetic/redacted fixtures and a provider budget. Review telemetry, local UI/MCP exposure, output retention and untrusted-PR behavior.
2. Compare Inspect AI with existing pytest/agent harnesses using a small fixed benchmark. Keep Docker sandbox and logs isolated; only evidence summaries enter CK-NEXUS.
3. Compare AgentClash replay, failure taxonomy and CI regression gates with the existing CK-NEXUS harness and the Promptfoo/Inspect AI prototypes; use only a separate worker, with no hosted account or production credentials.
4. Compare Letta Code memory/skills self-modification, hooks and permission modes with CK-NEXUS memory policy; do not install it or connect a Letta account, and require a separate sandbox plus strict mode before any later experiment.
5. Compare Langfuse v4.76 audit-log and data-minimization coverage with the existing OpenTelemetry/evidence pipeline; any future deployment belongs on separate infrastructure, not the current VPS.
6. Audit the existing browser adapter against a short Playwright conformance matrix. Add Playwright MCP only if it fills a measured gap and can be pinned, sandboxed and allowlisted.
7. Align AGNES skill metadata and validator checks with Agent Skills; pin every accepted skill source and hash.
8. Add a read-only MCP Registry discovery feed only after schema/version pinning, advisory checks, package provenance validation and a human approval queue.
9. Compare OpenSandbox against the native sandbox on a separate worker; verify runtime isolation, API-key enforcement, host-mount restrictions, per-sandbox egress, image provenance, cleanup and resource limits before any integration.
10. Review the OpenAI Agents SDK lock drift from 0.19.3 to 0.24.0 in an isolated dependency-upgrade change; run compatibility, privacy/tracing, sandbox and regression tests before changing the lockfile.

No package was installed, no community skill was executed, no credential or permission changed, no new account was connected, no service was deployed, and no Q10–Q16 artifact or gate was modified by this review.
