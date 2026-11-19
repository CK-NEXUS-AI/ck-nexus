# CK-NEXUS Value Expansion Addendum: Thailand AI Communities & Tool Ecosystem

- Date: 2026-11-19
- Parent research commit: `3a6ea55471b8fa3f905b250d78b4cc79ec3a8c4c`
- Branch: `research/ai-company-os-intel-20261119`
- Scope: public-source research, user-provided community link inventory, and proposed product differentiation. No Facebook group content was read, no groups joined, and no member data collected.

## Executive recommendation

Do not position CK-NEXUS as another wrapper around ChatGPT, DeepSeek, Claude, Gemini, Antigravity or NotebookLM. Position it as the governed operating layer that turns work done in those tools into reusable company capability:

**Community signal → evidence-backed insight → reusable skill/workflow → evaluation test → approved CK-NEXUS capability → measurable outcome.**

This creates compounding value: every accepted workflow can become a versioned skill, every incident becomes a regression test, and every verified task contributes to organizational knowledge.

## 1. Eight user-supplied Thai AI communities

The following links were supplied by the user. A public-page fetch of all eight returned `login_required`. The Facebook browser profile named `CK-NEXUS Facebook Market Intelligence` currently has no recorded Facebook sign-in. Therefore group descriptions, posts, activity levels, rules, and member content are **NOT VERIFIED**. This list is a source registry only, not evidence that the groups were inspected.

| # | Community / focus as supplied | User-provided URL | Potential CK-NEXUS use |
|---:|---|---|---|
| 1 | Thailand ChatGPT | https://www.facebook.com/groups/thailandchatgpt | Work patterns, prompts, repeatable workflows, ChatGPT integration feedback |
| 2 | DeepSeek R1 | https://www.facebook.com/groups/3123436451141602/ | Reasoning workflows, low-cost model use, structured output tests |
| 3 | Claude AI | https://www.facebook.com/groups/1583069816479976/ | Thai prompt patterns, coding and dashboard workflows |
| 4 | Google Antigravity / Vibe Coding | https://www.facebook.com/groups/1820330152540750/ | Agentic coding workflows, code review and test automation |
| 5 | Gemini / NotebookLM | https://www.facebook.com/groups/2189102768307258/ | Document research, source-grounded knowledge extraction |
| 6 | AI business / income | https://www.facebook.com/groups/1812695673266202/ | Business process pain points, automation opportunities, unit economics |
| 7 | AI upskilling | https://www.facebook.com/groups/1453537630086093/ | Skills taxonomy, training plans, reusable learning paths |
| 8 | AI Thailand Community | https://www.facebook.com/groups/1137249668646231/ | Emerging tools, ecosystem signals, new workflow patterns |

### Facebook access boundary

- Windsor.ai's connected Facebook account was previously verified for its Facebook Ads connector only. It is not evidence of access to these groups or organic Page/Group content.
- Meta's Content Library API documents public Facebook Pages, groups, events, profiles and posts, but access is through an approved secure research environment; downloading this content is not permitted. It is not a general-purpose CK-NEXUS scraping feed.
- Meta Page API access is permission- and feature-gated; Page-owned data requires the appropriate Page permissions and access conditions.
- For group research, use only user-authorized, platform-permitted access. Do not scrape private groups, bypass login or membership restrictions, collect personal profiles, or export member lists. Prefer user-submitted posts/exports where permitted, official APIs, public posts, and aggregate non-identifying observations.

## 2. The eight tools as capability sources, not dependencies

| Tool/community focus | Valuable capability to learn | CK-NEXUS integration stance |
|---|---|---|
| ChatGPT | Tool use, structured tasks, research, connectors and reusable instructions | Integrate through governed app/MCP or API adapters where officially supported; never depend on private ChatGPT UI scraping |
| DeepSeek | Reasoning mode, function/tool calls, JSON and schema-shaped outputs | Add provider adapter only after free-quota, data handling, timeout and JSON validation tests |
| Claude | Coding workflows, subagents, hooks, MCP and permission boundaries | Treat as an optional execution adapter; enforce CK-NEXUS policy outside the model |
| Antigravity | Agent manager, multi-agent coding, plan/diff inspection, asynchronous work | Study review and orchestration patterns; do not give it unbounded repo or deployment access |
| Gemini / NotebookLM | Long-document research and source-grounded synthesis | Import user-authorized research outputs with citations; NotebookLM is not assumed to offer a general public API |
| AI business workflows | Lead generation, marketing, sales, support, operations | Turn repeatable processes into approved business workflow templates; outbound actions remain approval-gated |
| AI upskilling | Skill discovery, training and evaluation | Build versioned Skill Registry with examples, rubric, owner, test suite and rollback |
| AI Thailand community | Trend discovery and tool discovery | Use as signal source, not a trusted technical authority; verify every claim against primary docs and code |

### Important provider/API facts

- DeepSeek's current API docs describe tool calls in thinking mode and structured JSON output; CK-NEXUS must validate returned tool arguments and JSON before acting.
- Antigravity's official docs describe a desktop command center, CLI, IDE surfaces and SDK with multi-agent orchestration; it is a potential adapter/reference pattern, not a substitute for CK-NEXUS authorization.
- LiteLLM documents cross-provider spend tracking and budgets, but budget enforcement requires a connected database; a DB-less configuration may fail open. If evaluated, test the hard-stop path with a real persistent DB before relying on it.
- OpenTelemetry's GenAI semantic conventions define spans for agent invocation and tool execution. These are useful as a standard event schema, but parts remain in development; version-pin and validate emitted attributes.
- OWASP's Top 10 for Agentic Applications 2026 is a useful threat-model checklist for agent identity, tool access, prompt injection and execution boundaries.

## 3. High-value CK-NEXUS product opportunities

### A. Skill Foundry — turn one-off prompts into tested capabilities

Input: a prompt, post, user workflow, incident, document or task transcript supplied with permission.

Pipeline:
1. Redact secrets and personal data.
2. Record source, timestamp, rights/permission basis and hash.
3. Extract the task intent, inputs, expected output and failure modes.
4. Convert it into a versioned Skill Contract.
5. Generate positive, negative, boundary and adversarial test cases.
6. Run in a no-network sandbox using synthetic or approved data.
7. Require independent reviewer approval before publishing to the shared skill catalog.
8. Track adoption, success rate, rework, latency and cost.

Proposed Skill Contract fields:
`skill_id`, `version`, `owner`, `purpose`, `inputs_schema`, `outputs_schema`, `required_capabilities`, `forbidden_capabilities`, `risk_class`, `approval_policy`, `evidence_requirements`, `test_suite_ref`, `source_lineage`, `license_basis`, `rollback_version`.

### B. Model Router + Cost Guard

- Route each task by quality requirement, data sensitivity, latency and price—not by model popularity.
- Prefer local/free providers only when they pass task-specific quality checks.
- Use a cheap model for classification/extraction and a stronger model only for ambiguous/high-impact tasks.
- Record estimated cost before execution and actual provider-reported usage after execution.
- Mark unknown prices as `UNPRICED`; never treat missing price as free.
- Enforce budgets at the gateway with persistent accounting, concurrency-safe reservations and a hard-stop test.
- Keep fallback attempts tied to the original task and original budget.

### C. Agent Passport & Zero-Trust Tool Gateway

Every agent receives:
- Stable agent identity and owner.
- Tenant and reporting line.
- Allowed tools and data scopes.
- Short-lived execution lease and credential references.
- Risk class and approval rule.
- Per-task budget ceiling.
- Immutable execution/evidence trail.

Every tool call is checked at runtime. Agent-to-agent delegation cannot widen permissions. A child agent inherits the intersection of parent authority and task-specific grants, never the union.

### D. Evidence-to-Value Loop

Each task should emit a standard record:
- goal and task ID
- responsible agent and reviewer
- source/evidence references
- plan and policy decision
- model/tool calls and usage
- test and verification result
- human approval record
- accepted/rejected outcome
- time, cost, quality and rework

This creates the data needed to answer: which AI role creates measurable value, which workflows should be automated, and which models are not worth their cost?

### E. Thai AI Workflow Marketplace (future product)

A curated catalog of Thai-language business skills:
- document and invoice extraction
- customer support draft workflows
- product research and competitor monitoring
- Thai/English translation and localization
- sales lead qualification
- policy and contract review assistance
- dashboard/report generation
- software QA and regression triage

Each listing must include owner, license/usage rights, tested models, sample input/output, eval score, risk label, cost estimate, required permissions and changelog. Start private/internal; public marketplace is a separate product decision.

## 4. Prioritized implementation roadmap

| Priority | Work item | Reuse first | Acceptance evidence |
|---:|---|---|---|
| P0 | Agent Passport + capability policy | Existing AI team models, credential capability registry, Policy Kernel | Permission tests prove least privilege and deny-by-default |
| P0 | Skill Foundry data contract | Existing Idea Engine and research lineage | Versioned skill + source lineage + reproducible eval |
| P0 | Evidence event schema | Existing Evidence Engine and audit paths; OpenTelemetry GenAI conventions as mapping reference | Agent/tool spans correlate to task, actor, policy and evidence |
| P1 | Model Router cost guard | Existing provider router/free providers; evaluate LiteLLM only if gaps remain | Persistent spend ledger, reservation, hard-stop and fallback tests |
| P1 | Workforce outcome dashboard | Existing task store/control plane | Completion quality, rework, cost, latency and verified outcome |
| P1 | Community signal intake | Existing research repository | Only authorized content; PII redaction, retention, provenance, deletion workflow |
| P2 | Thai Skill Marketplace | Existing skill catalog and capability fabric | License checks, test results, owner approval, version rollback |
| P2 | Public customer-facing Company OS | Existing multi-tenant/runtime foundations | Independent security review, tenant isolation and deployment evidence |

## 5. Competitive differentiation

Paperclip is a strong reference for agent org charts, goals, tasks, budgets, approvals, routines and runtime adapters. CK-NEXUS should not clone its dashboard or duplicate its orchestration surface. Its potential differentiation is the deeper governed execution and evidence chain:

- policy decisions are separate from agent proposals
- credentials are references, scoped to capability and lease
- sandbox and verification are explicit gates
- evidence lineage connects sources, actions, tests and outcomes
- skills are versioned and regression-tested
- cost limits are enforced before and during execution
- Thai-language business workflows and local operating context are first-class

The competitive claim is a hypothesis until a feature-by-feature and security comparison is completed.

## 6. Security, legal and cost guardrails

- No installation or code import based only on a social post or a tool's marketing claim.
- Check source repository, exact license, dependencies, maintenance, security advisories and data flows before reuse.
- Do not copy proprietary prompts, paid course materials, member-only posts or personal data.
- Do not scrape closed Facebook groups or circumvent access controls.
- Keep external messages, posts, ads, purchases, financial actions, permission changes and deployments approval-gated.
- Never claim a model or API is free without checking current pricing, quota and terms; a free UI tier does not imply a free API.
- Never set a budget cap without durable storage and a tested fail-closed enforcement path.

## 7. Source register

- Meta Content Library API overview: https://developers.facebook.com/docs/content-library-and-api/content-library-api/overview
- Meta Graph API Page reference: https://developers.facebook.com/docs/graph-api/reference/page/
- Paperclip project: https://github.com/PaperclipAI/paperclip
- Paperclip core concepts: https://github.com/paperclipai/paperclip/blob/master/docs/start/core-concepts.md
- DeepSeek tool calls: https://api-docs.deepseek.com/guides/tool_calls/
- DeepSeek thinking mode: https://api-docs.deepseek.com/guides/thinking_mode/
- DeepSeek JSON mode: https://api-docs.deepseek.com/guides/json_mode/
- Google Antigravity overview: https://antigravity.google/docs/overview
- LiteLLM spend tracking: https://docs.litellm.ai/docs/proxy/cost_tracking
- LiteLLM budgets: https://docs.litellm.ai/docs/proxy/users
- OpenTelemetry GenAI agent spans: https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md
- OpenTelemetry GenAI tool execution: https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/execute-tool.md
- OWASP Top 10 Agentic Applications 2026: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/

## 8. Current evidence status

- VERIFIED: eight group URLs were supplied by the user and stored as a source registry in this report.
- VERIFIED: public fetch attempts returned `login_required` for all eight; no group content was extracted.
- VERIFIED: the TinyFish Facebook browser profile has no Facebook sign-in recorded.
- VERIFIED: Windsor.ai Facebook Ads connector access is separate from Facebook Groups/organic content access.
- VERIFIED: public official documentation supports the cited product/API capabilities summarized above.
- NOT VERIFIED: group membership, post content, community activity, member counts, rules, group sentiment or admin permissions.
- NOT VERIFIED: whether CK-NEXUS currently has a complete persistent model budget enforcement path or complete agent identity enforcement across all execution routes.
- NOT IMPLEMENTED: Skill Foundry, Model Router hard-stop, Agent Passport enhancements or Marketplace in this addendum.
- NOT APPROVED: importing Paperclip, LiteLLM, Antigravity or any other external code into the production repository.
