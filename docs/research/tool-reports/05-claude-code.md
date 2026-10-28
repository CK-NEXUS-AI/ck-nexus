# Tool 05 — Claude Code (Anthropic)
Research date: 2026-10-25. Primary sources: https://docs.anthropic.com/en/docs/claude-code/getting-started, https://docs.anthropic.com/en/docs/claude-code, https://claude.com/pricing.

## 1. Identity
Claude Code is Anthropic's terminal-oriented coding agent. The client is proprietary; it is distributed through Anthropic's supported installation methods and can authenticate through Anthropic Console, a Claude Pro/Max subscription, or supported enterprise platforms such as Amazon Bedrock and Google Vertex AI. It is active and has rapidly expanded beyond single-session terminal work into subagents, skills, hooks, MCP and agent teams.

## 2. Category
Task Agent, with optional Multi-Agent behavior through subagents and agent teams. It is not a self-evolving framework by default: the model can plan and modify code, but persistent quality improvement requires external tests, metrics and governance.

## 3. Core Mechanism
Claude Code runs a model-driven tool loop in a terminal: inspect repository context, plan, call file/shell/search tools, observe results, and iterate. Project instructions and reusable Skills shape the workflow; hooks can enforce deterministic actions around tool events; MCP servers extend capabilities. Worktrees provide isolation for parallel changes, and subagents/agent teams can divide independent investigations or implementation tasks. These features are powerful only when tasks have clear ownership and agents do not write conflicting files. Anthropic's own prompting guidance warns that subagents can be overused when direct grep or a simple sequential operation would be cheaper.

## 4. Key Capabilities
Strong terminal-native codebase exploration; custom Skills and project instructions; hooks for repeatable guardrails; MCP integration; parallel subagents; Git/worktree workflows; and authentication choices that span subscription and API/enterprise platforms. Claude Code can be used from a local machine or a controlled remote development environment. Worktree isolation is a workflow feature, not a security boundary for secrets or network egress.

## 5. Evidence
Anthropic documents the supported installation, tool workflow and subagent behavior. SWE-bench Verified is a benchmark often cited in coding-agent discussions, but scores vary by model, harness, attempt budget, repository snapshot and evaluation protocol. No single benchmark score should be attributed to “Claude Code” without the exact model/harness/date. This report does not claim a current independent Claude Code-versus-Codex winner. A team should evaluate its own historical issues and measure accepted fixes, regression rate, wall time, token cost and human review time.

## 6. Limitations
The agent can execute powerful shell commands and modify files, so prompt injection, malicious repository instructions, dependency scripts and accidental destructive commands remain risks. Subagents can multiply token spend and duplicate work; independent-looking teammates may share the same underlying model/provider and are not automatically independent evidence. Subscription usage limits are not unlimited API access. Network availability and provider authentication are required for hosted inference. Human review and reproducible CI remain necessary.

## 7. Cost & Access
The official Claude pricing page currently lists Pro at $20/month when billed monthly or $17/month with annual billing, and Max from $100/month with higher usage tiers. Claude Code can also use Anthropic Console API billing or supported enterprise providers; those costs differ from the consumer subscription. Install with the official `@anthropic-ai/claude-code` package or current native installer instructions. Source: https://claude.com/pricing and https://docs.anthropic.com/en/docs/claude-code/getting-started. It is not an open-source self-hostable model; execution can be local while inference remains hosted.

## 8. Comparison
Compared with Codex CLI, Claude Code offers a mature terminal-first workflow with Skills/hooks and strong subagent patterns; Codex provides an open-source harness and explicit sandbox modes with app-server/SDK options. Compared with Cursor, Claude Code is easier to use headlessly and script, while Cursor packages a graphical editor and cloud agent experience. Actual cost depends on subscription/API billing and task length.

## 9. Verdict
Good for developers who need deep repository work, reusable workflows, terminal tool use and parallel investigations. Less suitable where all model inference must be offline or where agent permissions cannot be tightly scoped. For CK-NEXUS, use as a worker only in a worktree/container with least-privilege credentials, narrow network access, deterministic hooks/tests, and independent verification. Never let a Claude-generated report verify its own patch.

## Evidence gaps
No public evidence in the sources cited here proves universal production success rates or a single benchmark score transferable to CK-NEXUS. Recheck model-specific pricing and feature availability before procurement.
