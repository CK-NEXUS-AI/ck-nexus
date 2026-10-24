# Tool 01 — GitHub Copilot

Research date: 2026-10-25. Scope: official GitHub documentation and pricing plus the published controlled productivity study. Prices are USD and may vary by region/tax; verify again before purchase.

## 1. Identity
GitHub Copilot is GitHub's AI coding product (GitHub is part of Microsoft). The preview was announced in 2021 and general availability followed in 2022. It is a proprietary hosted service/client ecosystem; the official product is not an open-source self-hosted replacement. Current status: active, with IDE, CLI, GitHub-hosted coding agent, code review, model selection and agentic memory features. Official plan and feature source: https://github.com/features/copilot/plans and https://docs.github.com/en/copilot/get-started/plans.

## 2. Category
Primarily AI-Assisted, with Task Agent capabilities through agent mode, Copilot CLI and the cloud coding agent. It is not inherently a self-evolving system. Repository memory improves future context, but that is not equivalent to autonomously rewriting and validating its own implementation.

## 3. Core Mechanism
Copilot assembles prompt context from the user's request and permitted editor/repository context, then calls a hosted model. Agent modes can use tools and modify code; the cloud agent can research a task, work in a GitHub environment and create a pull request. Paid-plan Copilot Memory is in public preview and stores repository-specific facts and user coding preferences; GitHub says memories are validated against the current codebase and automatically expire after 28 days. Sources: https://docs.github.com/en/copilot/concepts/prompting-and-context/copilot-memory and https://github.blog/changelog/2026-01-15-agentic-memory-for-github-copilot-is-in-public-preview/.

## 4. Key Capabilities
- Works across common IDEs and GitHub workflows, with CLI, agent mode, code review and cloud agent.
- Offers a broad model catalog and, in eligible plans, third-party coding-agent delegation.
- Provides organization policy, seat management, audit/governance controls and IP indemnity on Business/Enterprise plans.
- BYOK exists in particular clients: the Copilot app announced provider-key support on 2026-06-23 for OpenAI, Azure OpenAI, Microsoft Foundry, Anthropic, LM Studio, Ollama and OpenAI-compatible endpoints. This must not be generalized to every Copilot client or every plan. Keys are stored in the local OS keychain for that app. Source: https://github.blog/changelog/2026-06-23-github-copilot-app-support-for-byok/.

## 5. Evidence
A controlled experiment published by Microsoft Research recruited developers to implement a JavaScript HTTP server; the treatment group with Copilot completed that specific task 55.8% faster than the control group. This is evidence for one bounded task under study conditions, not proof that every developer, repository, or agentic workflow is 55.8% faster. Source: https://www.microsoft.com/en-us/research/publication/the-impact-of-ai-on-developer-productivity-evidence-from-github-copilot/ (Peng et al., 2023). No public evidence from that study alone establishes the same gain for multi-agent autonomous production engineering.

## 6. Limitations
Model output remains probabilistic and requires tests, code review and security checks. Agentic sessions consume usage credits; costs vary with model, token volume and task complexity. GitHub's billing documentation says Business/Enterprise do not automatically fall back to a cheaper model when credits are exhausted; depending on policy, usage is blocked or metered. Memory is preview functionality and can be stale or incomplete despite validation. BYOK availability is client-specific. Hosted service access and model availability depend on GitHub policy, plan and provider availability.

## 7. Cost & Access
The official pricing page checked on 2026-10-25 lists Free at $0, Pro at $10/month, Pro+ at $39/month, and Max at $100/month. The current page describes the included monthly AI-credit value as $15 for Pro, $70 for Pro+, and $200 for Max; Free has limited chat/agent use and 2,000 completions monthly. Business and Enterprise pricing and included AI-credit rules are listed separately for organizations and may vary by billing terms. Because GitHub has revised its credit model and plan names over time, use the live plan page as the source of truth rather than carrying forward older per-seat credit figures: https://github.com/features/copilot/plans and https://docs.github.com/en/copilot/concepts/billing-and-usage/individuals/billing. Install through a supported IDE, GitHub or Copilot CLI. No official full-product self-host deployment was identified. BYOK applies only to supported clients/features and does not self-host Copilot's cloud agent or governance services.

## 8. Comparison
Compared with Cursor, Copilot is more tightly integrated with GitHub governance, repository workflow, code review and organizational billing; Cursor emphasizes its AI-native editor and integrated agent workflow. Official Cursor pricing page currently lists Free, Plus, Premium, Super and Ultra, with third-party model usage billed separately in eligible plans; the page's plan names/prices can change: https://cursor.com/pricing. Do not compare headline prices alone: compare included model usage, agent limits, privacy/admin controls and actual cost per accepted change. Versus VS Code without Copilot, Copilot adds inline completion, chat, model-driven agent and GitHub workflow integration, but adds vendor/service and usage-policy dependence.

## 9. Verdict
Best fit: developers and teams already using GitHub who want a low-friction assistant with a progression from completions to cloud PR-producing agents and centralized policy. Business/Enterprise are more suitable where access control, budgets, IP indemnity and governance matter. Less suitable when the hard requirement is a fully self-hosted coding-agent stack or provider-independent runtime across all clients. For CK-NEXUS, treat Copilot as an optional external coding tool, not as the Council authority: any proposed patch must pass the repository's own evidence, tests, security gates and exact-SHA verification.

## Evidence gaps
The 55.8% figure is task-specific and from 2023; it is not a 2026 head-to-head Copilot-versus-Cursor trial. Claims of persistent memory improving quality are documented as product behavior, but independent long-horizon causal evaluation is not established by the cited release note. No public evidence here establishes a guaranteed productivity gain for CK-NEXUS's particular workload.
