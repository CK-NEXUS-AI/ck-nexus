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
| not_connected | No CK-NEXUS Connector Fabric connection to this candidate was verified. | The service is globally unavailable. |
| not_integrated | No CK-NEXUS adapter/runtime wiring was demonstrated. | No source code or documentation exists. |
| runtime_verified | Pinned candidate was exercised through CK-NEXUS runtime and evidence captured. | A future version or different deployment subject. |

The existing status field remains the installation/inventory state (present, partial, discovery_only, not_installed or blocked). New candidates remain discovery_only. The additional verification_state object is research metadata; the current CapabilityCatalog loader ignores unknown metadata fields, so it does not activate or authorize anything.

All four candidates below have discovered=true, available_in_chat_session=false, online_verified=true, not_connected=true, not_integrated=true, runtime_verified=false and authority_scope=NONE.

## 3. Candidates reviewed

| Candidate | Version/date | License | Compatibility and footprint | Decision |
|---|---|---|---|---|
| [Agent Skills specification](https://github.com/agentskills/agentskills) | Living spec; no GitHub Releases observed 2026-11-09 | Apache-2.0 code; CC-BY-4.0 docs | Format only; no runtime dependency. Skills may bundle scripts. | Use as metadata/conformance reference only; pin commits and validate; no auto-install. |
| [Promptfoo](https://github.com/promptfoo/promptfoo) | 0.125.1 (2026-10-25) | MIT | Node.js >=22.22.0; Node 24 LTS recommended; substantial npm CLI footprint. | Highest-priority candidate for isolated CI evals and LLM/agent red-team tests. |
| [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) | 0.3.287 (2026-10-31; PyPI Trusted Publishing provenance observed) | MIT | Python >=3.11; broad dependency surface including cloud SDKs, FastAPI, numpy, fsspec/s3fs, textual and tiktoken. | Optional separate CI benchmark worker; not production dependency or VPS co-install. |
| [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) | 0.0.84 (2026-10-31) | Apache-2.0 | Node.js >=18 plus Playwright/browser engines; high disk/RAM footprint. | Evaluate only if existing CK-NEXUS browser adapter has a proven coverage gap. |

### 3.1 Agent Skills specification

Anthropic announced donation of the Agent Skills open standard to the Agentic AI Foundation under the Linux Foundation on 2026-10-22. The specification defines a portable SKILL.md folder format, progressive disclosure, optional compatibility metadata and an experimental allowed-tools field. The latter is not a security boundary and support may vary by client.

No GitHub Releases were published at review time. Pin a reviewed commit SHA and file hashes rather than relying on a floating branch or assumed semantic version. A skill is procedure/content, not an identity, credential, permission grant or authority source.

### 3.2 Promptfoo

Promptfoo is a CLI/library for prompt, model, agent and RAG evaluation plus red-team testing. Official docs list 157 red-team plugins across security/access-control, privacy, trust/safety and other categories. Its upstream README says Promptfoo is now part of OpenAI and remains MIT-licensed.

Security caveat: Promptfoo OSS documents no general sandbox for adversarial eval content. Configs, scripts, providers, datasets and pull-request content must be treated as trusted code/data. Run untrusted inputs in an isolated container/VM with least-privilege credentials and restricted egress. Its local web UI/MCP runs with the invoking user's permissions and is not a security boundary; do not expose it to untrusted networks. Telemetry opt-out is not a general egress firewall. Provider/model usage and test volume create variable cost, so impose explicit limits.

### 3.3 Inspect AI

Inspect AI provides task/dataset-based evaluations, solvers, scorers, model graders, tool-use tests, evaluation logs, tracing, retries, concurrency controls and time/message/token/cost limits. Docker sandbox support is available for tools explicitly routed through the sandbox interface. Provisioning a container alone does not isolate arbitrary evaluator code.

The 0.3.287 PyPI release includes Trusted Publishing provenance pointing to the official GitHub repository and release workflow. Its broad Python dependency surface warrants a dedicated evaluation environment rather than the canonical CK-NEXUS application image. Model API usage and worker compute remain metered.

### 3.4 Microsoft Playwright MCP

Playwright MCP exposes browser navigation, accessibility snapshots, interaction, JavaScript evaluation, cookies/storage, optional network/devtools capabilities, tracing and test assertions. Release 0.0.84 adds named isolated browser contexts and configurable URL-parameter redaction.

The upstream README explicitly states that Playwright MCP is not a security boundary. Browser tools can mutate authenticated websites and access session state. Configure explicit allowed hosts/origins, restricted workspace roots, least-privilege browser profiles, loopback binding and egress controls. Do not use --no-sandbox or unrestricted file access for untrusted pages. URL redaction is convenience, not a security control.

For coding-agent flows, upstream documentation recommends considering Playwright CLI plus Skills for lower schema/token overhead. MCP remains useful for persistent browser state, exploratory automation and self-healing test loops. CK-NEXUS already has browser-automation scaffolding; compare it before introducing a second browser control surface.

## 4. ChatGPT session tool inventory (session-only)

These namespaces were exposed in the current ChatGPT tool catalog. This is a session-availability snapshot, not proof that each external account is authenticated or that CK-NEXUS can call these services.

| Area | Namespaces exposed | State |
|---|---|---|
| Repository/developer workflow | GitHub | available_in_chat_session=true; repository read access was exercised in this review. |
| UI/design | Figma, Canva | available_in_chat_session=true; tool definitions surfaced; no design action/account access tested. |
| Browser/research | TinyFish | available_in_chat_session=true; tool definitions surfaced; no live browser task run. |
| Build/deploy | Vercel, Replit, Lovable, Base44, Wix | available_in_chat_session=true; no project modified or deployed. |
| Knowledge/data/workspaces | Notion, Slack, Hugging Face, Supabase, Neon, MongoDB Atlas, Soluvery, Granola, Airtable, Asana, Linear, monday.com | available_in_chat_session=true; no account data read or changed for this inventory. |
| Remote operations | Remote Desktop Commander | available_in_chat_session=true; device inventory inspected only. |

For these session tools, not_connected and not_integrated refer specifically to CK-NEXUS Connector Fabric/runtime. They remain true unless a CK-NEXUS-side connection and integration are demonstrated. Their authority scope is always NONE. A ChatGPT connector exposed in this session does not make it a CK-NEXUS Runtime plugin.

The ChatGPT Skills listing returned an empty list in this session. Plugin-management functions exposed dependency and permission operations but no marketplace-wide plugin discovery/list operation; therefore this review does not claim a complete marketplace inventory.

## 5. Existing CK-NEXUS baseline

- config/capability_catalog.json is canonical; the legacy external-registry JSON path was absent from reviewed main.
- The existing agnes-skills entry remains present; this review adds Agent Skills only as a discovery-only format reference. No community skill was installed.
- Promptfoo and Inspect AI complement existing tests/security gates; they do not replace Q10–Q16 evidence or independent review.
- Playwright MCP is not considered installed because browser scaffolding exists or ChatGPT exposes TinyFish. Existing browser code must be assessed before another adapter is added.
- Existing LangGraph, Letta, Langfuse and workflow candidates remain discovery-only; no competing orchestration, memory, observability or workflow plane is proposed.

## 6. Next evaluation order

1. Prototype Promptfoo in isolated, non-production CI with synthetic/redacted fixtures and a provider budget. Review telemetry, local UI/MCP exposure, output retention and untrusted-PR behavior.
2. Compare Inspect AI with existing pytest/agent harnesses using a small fixed benchmark. Keep Docker sandbox and logs isolated; only evidence summaries enter CK-NEXUS.
3. Audit the existing browser adapter against a short Playwright conformance matrix. Add Playwright MCP only if it fills a measured gap and can be pinned, sandboxed and allowlisted.
4. Align AGNES skill metadata and validator checks with Agent Skills; pin every accepted skill source and hash.

No package was installed, no community skill was executed, no credential or permission changed, no new account was connected, no service was deployed, and no Q10–Q16 artifact or gate was modified by this review.
