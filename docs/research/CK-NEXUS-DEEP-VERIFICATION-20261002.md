# CK-NEXUS Deep Verification — New Discovery Candidates — 2026-10-02

## Verification rule

A candidate is SOURCE_VERIFIED only when current evidence supports the stated identity, capability, license or security property. A directory listing alone is not sufficient. ADMITTED is reserved for a later CK-NEXUS integration/reproduction gate.

## Results

| Candidate | Identity / capability | License | Security / privacy evidence | Pricing/free | Current CK-NEXUS state |
|---|---|---|---|---|---|
| Agno | Verified agent framework/runtime/platform; human approval, audit logs, JWT RBAC, A2A and MCP documentation | Apache-2.0 | Current GitHub security page says no SECURITY.md; telemetry is enabled per agent run by default and can be disabled with AGNO_TELEMETRY=false | Official pricing states Free runtime/SDK and AgentOS at $0; Pro is $150/mo for live control-plane operation | SOURCE_VERIFIED / SECURITY_REVIEW_REQUIRED |
| Activepieces | Verified AI agents, MCPs and workflow automation; community edition | MIT for core/community edition; enterprise is commercial | SECURITY.md exists; current security page lists multiple 2026 advisories, including high-severity sandbox/code issues | Community/self-hosted path exists; enterprise features require commercial licensing | SOURCE_VERIFIED / SECURITY_REVIEW_REQUIRED |
| Aider | Verified terminal AI pair-programming tool; works with cloud and local LLMs | Apache-2.0 | Repository identity and source verified; deeper security review not yet performed | No current free-service pricing claim admitted; model/API costs can apply | SOURCE_VERIFIED / PRICING_REVIEW_REQUIRED |
| Chrome DevTools MCP | Verified MCP server for controlling/inspecting Chrome through DevTools; screenshots, network inspection, debugging and automation | Apache-2.0 | Official README warns browser content is exposed to MCP clients; Google usage statistics are collected; supports isolated/headless modes | No paid/free admission made; npx distribution verified | SOURCE_VERIFIED / SECURITY_REVIEW_REQUIRED |
| Context7 MCP | Verified MCP server for up-to-date code documentation | MIT | Official registry warns projects are community-contributed and security/accuracy are not guaranteed; API key is optional for higher limits/private repositories | API-key-free baseline documented; no blanket unlimited/free admission | SOURCE_VERIFIED / SECURITY_REVIEW_REQUIRED |
| MarkItDown MCP | Verified Microsoft MCP server, STDIO/Streamable HTTP/SSE, document-to-Markdown conversion | MIT for markitdown-mcp package | Official docs state local/trusted-agent use; HTTP/SSE defaults to localhost and warn against exposing other interfaces; I/O runs with current-process privileges | No paid/free-service claim needed for local package | SOURCE_VERIFIED / SECURITY_REVIEW_REQUIRED |
| A2A Protocol | Verified official Linux Foundation project/open standard for agent interoperability; official SDKs and TCK exist | Open-source project; exact per-repo license should be pinned before admission | Protocol project identity verified; deployment/security properties depend on each implementation | Not a hosted free tool; protocol/SDK discovery only | SOURCE_VERIFIED / IMPLEMENTATION_REVIEW_REQUIRED |
| A2A Registry | Discovery concept verified, but registry implementation requires separate repository/version/security review | NOT YET VERIFIED | NOT YET VERIFIED | NOT APPLICABLE | DISCOVERED |
| MCP Registry | Discovery catalogue verified, but individual servers require separate audit | NOT APPLICABLE at catalogue level | Individual server risk varies | NOT APPLICABLE | SOURCE_VERIFIED / SERVER-AUDIT_REQUIRED |
| Actionbook | Directory discovery only | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | DISCOVERED |
| AgentDock | Directory discovery only | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | DISCOVERED |
| AgentRunner | Directory discovery only | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | DISCOVERED |
| Aembit | Directory discovery only | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | DISCOVERED |
| AgentOps | Directory discovery only | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | DISCOVERED |
| AI Tool Directory MCP Server | Directory discovery only | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | DISCOVERED |

## Important security findings

### Activepieces
The project has a published security policy, but its current GitHub security page also lists 2026 vulnerabilities, including high-severity issues involving code/sandbox boundaries. One published advisory describes a V8 isolate sandbox bypass affecting versions <=0.79.4 and a patched version 0.80.0. Therefore, having a security policy must not be interpreted as currently secure or production safe.

### Agno
Agno documents human approval, audit logs and JWT-based RBAC, but the current repository security page reports no SECURITY.md. Its README also documents per-run telemetry and an opt-out environment variable. CK-NEXUS should therefore keep security admission separate from feature/license verification.

### Chrome DevTools MCP
The official project explicitly states that browser content is exposed to MCP clients and warns users not to share sensitive or personal information. This is a direct CK-NEXUS permission-boundary concern. It should run behind CK-NEXUS browser-session policy, not as unrestricted root/browser authority.

### MarkItDown MCP
The official project warns that conversion runs with the current process's I/O privileges. This makes sandboxing and URI/input allowlisting important when used by autonomous agents.

## Admission decision

No new candidate is ADMITTED by this report.

The following are eligible for the next reproducible CK-NEXUS sandbox gate:

1. Agno
2. Activepieces
3. Aider
4. Chrome DevTools MCP
5. Context7 MCP
6. MarkItDown MCP
7. A2A protocol/SDK

The remaining discovery candidates stay DISCOVERED until official identity, license, security, and runtime evidence is collected.

## Evidence sources

- Agno GitHub: https://github.com/agno-agi/agno
- Agno pricing: https://www.agno.com/pricing
- Activepieces GitHub/security: https://github.com/activepieces/activepieces
- Aider GitHub: https://github.com/Aider-AI/aider
- Chrome DevTools MCP: https://github.com/ChromeDevTools/chrome-devtools-mcp
- Context7 MCP Registry: https://github.com/mcp/upstash/context7
- MarkItDown MCP: https://github.com/microsoft/markitdown
- A2A Project: https://github.com/a2aproject

No credentials, OAuth grants, paid actions, production mutations, or account creation were performed.
