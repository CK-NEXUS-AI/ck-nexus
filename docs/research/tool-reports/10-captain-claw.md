# Tool 10 — Captain Claw
Research date: 2026-10-25. Primary sources: https://github.com/kstevica/captain-claw, https://captain-claw.com/docs/.

## 1. Identity
Captain Claw is a self-hostable multi-agent framework by the public GitHub maintainer `kstevica`. Its official site lists release 0.8.0 dated 15 October 2026 and describes the project as MIT-licensed, Python 3.11+, with a web research workspace and Flight Deck. Verify the repository LICENSE and pinned release tag before production deployment.

## 2. Category
Multi-Agent orchestration with proactive/autonomous workflow features. The project documents a “dream cycle” and a notice→decide→act→judge→learn loop, but this should be described as system-level self-optimization, not model-weight self-training or proven recursive intelligence.

## 3. Core Mechanism
Captain Claw combines an LLM provider layer, specialist agents, a shared virtual file system, multi-layer memory, tool registry, scheduler and Flight Deck UI. It offers ensemble reasoning, plan/deep modes, deterministic flows, parallel spawn/join, persistent topics and an autonomous-work arbiter that chooses a bounded action per heartbeat. Outcomes update reliability weights and a trust ladder can promote reversible actions when evidence supports it. The documentation also describes explicit intention/approval paths and kill switches for Gmail sending/auto-replies. These are promising architectural controls but must be tested against the deployed version and configuration.

## 4. Key Capabilities
The project claims 7 orchestration modes, 51 built-in tools, 6 shared memory layers and 31 specialist roles. It includes shell/file/browser/PDF tools, Google Workspace and Microsoft 365 integrations, persistent memory, scheduler, MCP server, a research UI and optional device clients. Provider choices include OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter and local Ollama. Some no-key access paths are mediated by separate CLI/subscription products and must not be treated as universal free API access.

## 5. Evidence
The GitHub repository and official docs verify that the project advertises these components and provide installation instructions. Counts such as 51 tools and 31 specialists are repository self-reported inventory metrics; they do not demonstrate correctness, reliability or security. No independent benchmark was found in this pass that verifies the quality of its memory or “dream cycle.” The closest verifiable evidence is source code, release notes, and tests at a pinned commit; a production evaluation should inspect each tool permission and run adversarial tests.

## 6. Limitations
Broad tool access, especially shell, email, Google Drive and browser actions, creates a large blast radius. The project supports many integrations, but each connection needs explicit credentials and scopes; a listed integration is not proof the user's accounts are connected. Memory can preserve mistaken information. Autonomous email and workspace edits can create privacy and accidental-send risks; the documented default-off send controls should remain off until recipient allowlists, daily limits, duplicate suppression and audit logs are verified. Running a fleet on a small VPS may overwhelm RAM/CPU.

## 7. Cost & Access
MIT-licensed self-host install is available with `pip install captain-claw`; the docs require Python 3.11+ and at least one inference path: paid provider key, eligible subscription/CLI login, or Ollama for local inference. Local models avoid API fees but consume compute and may be weaker. Optional voice features may require an additional Soniox key. Docker deployment is documented. Source: https://captain-claw.com/docs/.

## 8. Comparison
Compared with Hive, Captain Claw is broader and more general-purpose, with user-facing memory, workspace and communication tools; Hive specializes in governed repository maintenance. Compared with CK-NEXUS, Captain Claw offers an attractive reference architecture but would duplicate several existing modules (Council, MCP, provider routing, research and watchdog). Integrate selected patterns instead of installing a second control plane on the same VPS.

## 9. Verdict
Best for a technically capable user who wants a self-hosted agent command center and is willing to audit integrations. Not a plug-and-play production security boundary. For CK-NEXUS, study its deterministic Flow DSL, trust ladder, read-back verification and explicit email kill switches; do not install the full stack until resource and threat-model tests pass.

## Evidence gaps
No independent evidence found here validates a claimed autonomous quality gain or long-run reliability. Feature counts should be checked against the exact release tag and active tests.


### Additional operational assessment
Before deployment, inventory every enabled tool and map each one to a capability class: read-only, reversible write, externally visible write, or privileged execution. Google Workspace and Microsoft 365 integrations should be disabled by default until OAuth scopes and per-user identity isolation are confirmed. A self-hosted app still transmits prompts to whichever model provider is configured, so the data boundary follows the provider, not merely the host. Test the email kill switch, recipient allowlist, daily cap, duplicate suppression and audit trail with a fake mailbox before connecting a real account. On a low-memory VPS, run the research UI and one worker first; add concurrency only after measuring peak resident memory and queue latency.
