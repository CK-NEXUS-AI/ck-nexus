# Tool 02 — Cursor (Anysphere)
Research date: 2026-10-25. Primary sources: https://cursor.com/docs, https://cursor.com/docs/models-and-pricing, https://docs.cursor.com/background-agent, https://docs.cursor.com/context/rules-for-ai.

## 1. Identity
Cursor is an AI-focused code editor developed by Anysphere. It is a commercial, proprietary product built around a VS Code-derived editor experience; no official self-hosted full Cursor service is documented. The product is active and changes rapidly, so pricing and model availability should be rechecked at purchase time. Official documentation and release pages are the best evidence for feature status; no public independent audit was found that verifies all vendor performance claims across real production repositories.

## 2. Category
Cursor ranges from AI-Assisted editing to Task Agent workflows. Its foreground Agent can plan, search, edit, and run commands; Cloud/Background Agents can work asynchronously in remote VMs. That is agentic task execution, not proof of self-evolving software: a model may revise code and tests, but a separate trustworthy acceptance oracle is still required.

## 3. Core Mechanism
Cursor combines editor context, repository indexing/search, model selection, reusable rules, tools/MCP and agent loops. Project Rules live in `.cursor/rules`; user rules are global; `AGENTS.md` is supported; legacy `.cursorrules` remains supported but is deprecated. Rules are prompt context, not deterministic enforcement by themselves. Background Agents run in isolated Ubuntu-based machines with network access and can install packages; they clone permitted repositories through the GitHub app, run commands, edit code, and return results/PRs. Cursor's docs warn that terminal commands are automatically run by background agents, creating prompt-injection and data-exfiltration risks if the agent is tricked into contacting malicious sites. Sources above.

## 4. Key Capabilities
Composer and the editor-native Agent offer multi-file code changes; model choice spans Cursor and third-party models depending on plan; background agents can run without the local editor staying open; MCP, skills, hooks and reusable rules extend workflows. Cloud agents can provide logs and visual artifacts, and supported automations can start work from events or schedules. These features are useful when a developer wants an integrated editor and async execution rather than assembling a CLI agent manually.

## 5. Evidence
Official Cursor documentation verifies product behavior and plan mechanics, but product documentation is not an independent benchmark. No public, independently controlled 2026 head-to-head trial was found here that establishes Cursor is universally more productive than GitHub Copilot. Cursor's own documentation describes cloud agents as running for minutes or hours, but that is a capability description rather than a success-rate statistic. For comparison, use task completion rate, accepted PR rate, regression rate, and cost per accepted change on the same repository—not anecdotal speed claims.

## 6. Limitations
Background agents have network access and access to the configured repository, dependencies and permitted secrets; isolated VMs reduce local-host exposure but do not eliminate supply-chain or data-exfiltration risks. Agent instructions/rules can be ignored or misinterpreted and are not a substitute for CI policy. Usage can be model- and token-dependent; plans and included pools have changed over time. The editor is proprietary and cannot be deployed entirely on the user's VPS as a self-hosted equivalent. Large tasks may still require human review and may fail despite extensive tool use.

## 7. Cost & Access
The current pricing documentation checked on 2026-10-25 lists Hobby Free, Plus $8/month, Premium $30/month, Super $100/month, Ultra $200/month, with Teams tiers and Enterprise custom pricing. The current product/plan bundle has shifted over time; older pages still describe legacy Pro/Business names and different included usage, so the current Cursor pricing page is authoritative. Third-party models are billed at API list price from prepaid credits on eligible tiers; background/cloud agent usage consumes model usage. Source: https://cursor.com/docs/models-and-pricing and https://cursor.com/pricing. Install the desktop editor; self-hosting the complete commercial product is not supported. BYOK/third-party provider use is plan-dependent and not a universal free route.

## 8. Comparison
Compared with GitHub Copilot, Cursor prioritizes a unified AI-native editor and background agent UX; Copilot is more deeply integrated into GitHub governance, repository PR workflow and organization policy. Compared with Claude Code or Codex CLI, Cursor gives a graphical editor and indexing/rules in one product, while CLI agents are easier to embed in scripts and headless CI. Pricing must be compared by actual token consumption and accepted changes, not the nominal subscription alone.

## 9. Verdict
Best for developers who want a high-context AI editor, multi-file edits, and remote asynchronous coding. Less suitable for fully offline/self-hosted requirements or organizations needing all execution to remain on their own infrastructure. For CK-NEXUS, treat Cursor as an optional implementation agent; require isolated worktrees, constrained credentials/network access, tests, review, and Capability Authority before any merge or deployment. Do not let a Cursor rule file act as the sole security control.

## Evidence gaps
No public evidence found in this research pass establishes a universal 2026 productivity advantage over Copilot or a guaranteed agent success rate. Composer model behavior and plan limits are fast-moving and need a dated re-check before adoption.
