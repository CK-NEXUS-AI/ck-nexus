# Tool 06 — OpenAI Codex CLI
Research date: 2026-10-25. Primary sources: https://github.com/openai/codex, https://help.openai.com/en/articles/11096431, https://developers.openai.com/api/docs/guides/agents-api/overview, https://developers.openai.com/api/docs/guides/agents-api/multi-agent.

## 1. Identity
Codex CLI is OpenAI's open-source terminal coding-agent harness. The CLI and related app-server/SDK components are published openly; model inference and hosted Codex services remain separate commercial services. It is active and supports local execution, cloud Codex workflows, MCP, programmatic integration and subagents. The exact release/version should be pinned before production use.

## 2. Category
Task Agent with Multi-Agent capabilities when subagents are enabled. It is not automatically self-evolving: the harness can iterate, test and delegate, but quality improvement depends on an external acceptance oracle and policies.

## 3. Core Mechanism
The CLI operates from a repository and uses a tool loop to inspect/edit/run code. Its approval/sandbox modes govern which operations are permitted. OpenAI's newer Agents API separates a managed harness, an execution environment and the application server; the environment may be OpenAI-hosted or self-hosted. The managed harness can retain sessions, compact context, resume work and delegate to parallel subagents. MCP tools can be connected with scoped `allowed_tools`; self-hosted sandboxes run an executor that connects outbound to the service. Sources above.

## 4. Key Capabilities
- Open-source CLI and app-server/SDK integration surface.
- Sandboxed command execution and explicit approval controls.
- Subagent delegation for independent exploration, debugging and review.
- MCP connections and scripted/CI usage.
- Can run in user-controlled compute via a self-hosted executor; this does not make the hosted harness or model inference fully local.
- The current CLI/ChatGPT experience includes agent view, multi-agent tools, voice and worktree support according to OpenAI help documentation.

## 5. Evidence
Official documentation verifies architecture, subagent lifecycle and sandbox options. OpenAI's managed Agents API charges model use at selected model API rates and hosted sandbox compute at standard container rates; it is not a free unlimited service. The documentation explicitly warns that agents can access files, credentials and network available to their environment. No independent benchmark in the cited pages proves a universal Codex advantage over Claude Code. Benchmark comparisons must pin model, harness version, sandbox, retry budget and test data.

## 6. Limitations
CLI sandboxing reduces risk but does not remove prompt injection, supply-chain or misconfiguration risks. In a self-hosted environment, agent processes can reach whatever files and credentials the executor exposes. OpenAI's Agents API currently has specific data residency and retention constraints; self-hosting the execution environment does not automatically imply Zero Data Retention. Hosted API and compute costs can rise with long sessions and parallel agents. Some older MCP server instructions are obsolete: current documentation says `codex mcp-server` was removed in favor of app-server integrations.

## 7. Cost & Access
Codex CLI is free to install and open-source; inference can be accessed through supported ChatGPT subscription sign-in or OpenAI API usage depending on product path and policy. Agents API usage is billed by model and hosted sandbox resources. API keys and permissions are required for API-managed sessions. Installation and current access: https://github.com/openai/codex and https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan. Self-hosted execution is possible for supported Agents API workflows, but the harness may remain hosted.

## 8. Comparison
Compared with Claude Code, Codex exposes an open-source harness and programmatic app-server/SDK integration; Claude Code has its own Skills/hooks and consumer subscription path. Compared with OpenHands, Codex has a tighter integration with OpenAI's model/runtime ecosystem, while OpenHands emphasizes provider-agnostic open-source and enterprise self-hosting. Neither eliminates the need for least privilege and independent CI.

## 9. Verdict
Strong option for CK-NEXUS because its CLI can run in a bounded worktree and its app-server/SDK offers a programmatic integration path. Prefer local/sandboxed execution for sensitive code, restrict allowed tools, separate credentials from agent-generated code, cap parallelism and spend, and make test/review gates authoritative. Do not equate “sandboxed” with “safe for unrestricted production changes.”

## Evidence gaps
No public evidence here confirms the user-specific quota, free allowance, or a guaranteed 1–30 minute cloud runtime for all tasks. Runtime duration and cost must be measured from actual sessions.
