# CK-NEXUS New Discovery Sweep — 2026-10-02

**Purpose:** Find candidate AI/agent infrastructure that is not represented in the original 107-entry intake.

**Evidence rule:** Discovery is not admission. Pricing, security, licensing, API/MCP scope, privacy, and reproducibility remain AUDIT_PENDING unless separately verified.

## Newly discovered candidates

| Candidate | Class | Why it is new/relevant | Evidence source | Status |
|---|---|---|---|---|
| Actionbook | Browser-agent / automation | Listed as an AI-powered browser-agent workflow product | 345tool directory | DISCOVERED |
| AgentDock | AI agent builder | Visual AI agent builder; relevant to agent construction layer | 345tool directory | DISCOVERED |
| AgentRunner | Agent automation platform | Enterprise AI automation platform candidate | 345tool directory | DISCOVERED |
| Aembit | Agent identity / access | Relevant to workload/agent identity and secure access | 345tool directory | DISCOVERED |
| AgentOps | Agent observability | Agent infrastructure/observability candidate | ToolDirectory.AI | DISCOVERED |
| Agno | Agent framework | Developer framework for AI agents | ToolDirectory.AI | DISCOVERED |
| Activepieces | Workflow automation | Open/freemium workflow automation candidate | ToolDirectory.AI | DISCOVERED |
| Aider | Coding agent | Coding-agent capability candidate; listed as Free | ToolDirectory.AI | DISCOVERED |
| AI Tool Directory MCP Server | MCP | MCP server specifically for AI-tool discovery | ToolDirectory.AI | DISCOVERED |
| MCP Registry | MCP ecosystem | Official/community discovery layer for MCP servers | GitHub MCP registry | DISCOVERED |
| A2A Registry | Agent discovery | Directory of live hosted agents using A2A | GitHub A2A Registry | DISCOVERED |
| Awesome AI Agents | Ecosystem index | Machine-readable broad agent ecosystem index | GitHub repository | DISCOVERED |
| Chrome DevTools MCP | Computer-use / browser tooling | MCP server exposing Chrome DevTools | GitHub MCP registry | DISCOVERED |
| Context7 | Developer context | Up-to-date code documentation exposed through MCP | GitHub MCP registry | DISCOVERED |
| Markitdown MCP | Document ingestion | Converts document/media formats to Markdown through MCP | GitHub MCP registry | DISCOVERED |

## Source observations

### 345tool
The directory currently states 12,000+ AI tools/free utilities and exposes categories including AI Programming and Dev Framework. Its directory includes Actionbook, AgentDock, AgentRunner and Aembit among many other entries.

### ToolDirectory.AI
The current index reports 2,611 tools and explicitly distinguishes Free, Freemium, Paid and Free Trial. It lists AgentOps, Agno, Activepieces, Aider and an AI Tool Directory MCP Server.

### MCP Registry
The GitHub MCP registry currently exposes a community server catalogue. Current surfaced entries include Markitdown, Netdata, Context7 and Chrome DevTools MCP.

### A2A Registry
The A2A Registry describes itself as a discovery layer for live hosted agents implementing the A2A Protocol. It uses agent cards and health/conformance checks.

### Awesome AI Agents
The repository describes a broad ecosystem directory covering frameworks, coding agents, computer-use agents, orchestration, protocols, evals, memory, observability, marketplaces, security and sandboxes. It also states that a machine-readable agents.json exists.

## Important distinction

These sources are **discovery indexes**, not CK-NEXUS verification evidence.

For each candidate, the next gates are:

1. Official repository/domain
2. Current license
3. Current pricing/free limits
4. API/MCP/A2A surface
5. Authentication/OAuth scope
6. Secrets handling
7. Network/data-flow
8. Privacy/retention/training
9. Dependency/supply-chain posture
10. ARM64/Termux compatibility where relevant
11. Safe reproducible local test
12. CK-NEXUS admission decision

**No candidate is admitted from this sweep alone.**
