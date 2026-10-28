# Tool 16 — Qodo
Research date: 2026-10-25. Primary sources: https://www.qodo.ai/pricing/, https://www.qodo.ai/features/qodo-agentic-toolbox/, https://www.qodo.ai/blog/introducing-qodos-agentic-toolbox/.

## 1. Identity
Qodo is a commercial AI code-quality and code-review platform, formerly associated with the CodiumAI brand. Its 2026 Agentic Toolbox exposes context, rules and review skills to coding agents. The product is proprietary SaaS with enterprise options including on-premises or single-tenant deployment; exact licensing differs by component and contract. The current Agentic Toolbox launch announcement is dated 9 September 2026.

## 2. Category
Governance and verification layer for AI-assisted/agentic development. It uses specialized review agents and rule systems, but should not be treated as a general autonomous coding orchestrator or self-evolving codebase by itself.

## 3. Core Mechanism
Qodo connects repository context, pull request history, specifications and live Git state to an agent. Its toolbox provides skills over MCP for codebase questions, review of committed/uncommitted changes, rule retrieval and issue resolution. Qodo describes agent-to-agent review as an independent reviewer evaluating implementation work before PR creation. It also manages organizational standards and can surface structured findings for an implementation agent to resolve. “Independent” here is an architectural role distinction; the reviewer may still share provider/model biases unless configured and measured otherwise.

## 4. Key Capabilities
- Cross-repository context and impact analysis.
- Independent code review before opening a PR.
- Rules management and application of standards at the start of a task.
- PR review findings converted into structured follow-up actions.
- MCP integration with Claude Code, Codex, Kiro and other compatible agents.
- Enterprise governance, analytics, SSO/SAML, audit logs, BYOK and on-prem/single-tenant options on eligible plans.

## 5. Evidence
Official Qodo materials document the toolbox capabilities and pricing. The current Pro Team page lists $30/month, a 14-day free trial, credit packs at $0.012 per credit, and approximate examples of 2,500 credits for about 18 reviews, 5,000 for about 36, and 20,000 for about 144 reviews. These are vendor pricing examples; review consumption depends on PR complexity. No independent benchmark in this pass proves a particular reduction in defects or reviewer hours. Evaluate precision/recall of findings and false-positive rates on a labeled set of the team's historical PRs.

## 6. Limitations
AI review can miss vulnerabilities or produce false positives. If implementation and review agents share the same model, prompt context or flawed acceptance criteria, their errors may be correlated. A rule registry does not enforce behavior if agents skip it; deterministic CI and branch protection must enforce critical constraints. Enterprise on-prem capabilities require a commercial contract. Usage is credit-based and can be hard to predict without a pilot.

## 7. Cost & Access
The official pricing page lists Pro Team at $30/month with a 14-day trial; credit packs are billed at $0.012/credit, and enterprise is custom-priced. Enterprise features include SSO/SAML, audit logs, BYOK and single-tenant SaaS or on-prem deployment. Source: https://www.qodo.ai/pricing/. The toolbox can be installed through its official CLI or agent plugin/MCP workflow; account login is required. No permanent free tier is advertised for Pro Team, though qualifying open-source projects may apply for a program.

## 8. Comparison
Compared with GitHub Copilot Code Review, Qodo emphasizes cross-repository context, organization rules and agent-in-the-loop local review; Copilot is more tightly integrated with GitHub PR workflows and its native plan/credit model. Compared with Constraints Registry, Qodo supplies probabilistic code review/context and workflow tooling, while a constraints registry can expose versioned requirements and deterministic validators such as OPA/Checkov/Semgrep. These are complementary, not direct substitutes.

## 9. Verdict
Useful for teams where review bottlenecks and architectural context are material problems. For CK-NEXUS, trial Qodo on a small set of non-sensitive PRs and compare against existing tests, secret scanning and reviewer findings. Do not treat a green Qodo review as a deployment authorization; keep signed Capability Authority grants and deterministic CI as independent controls.

## Evidence gaps
No public evidence found here establishes that Qodo's agent-to-agent review is statistically independent or universally more accurate than Copilot review. The pricing page is authoritative for vendor terms but not for quality outcomes.
