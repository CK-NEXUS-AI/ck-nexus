# CK-NEXUS Development Assistant Fabric V1

Status: **Post-P0 development only**  
Authority: **CK-NEXUS**  
Production status: **NO-GO**

## Objective

Use multiple maintained open-source or free-entry developer assistants to speed up
research, implementation, review, testing, and issue fixing without granting any
third-party agent authority over CK-NEXUS state, policy, credentials, production,
or release evidence.

Open-source software does **not** imply free model inference. The fabric therefore
separates tool licensing from model/provider cost and prefers local/free-entry
routes when they are available.

## Active routing candidates

| Assistant | Upstream | License / free-entry path | Best use |
|---|---|---|---|
| OpenCode | https://github.com/anomalyco/opencode | MIT; open-source CLI | existing CK-NEXUS bridge, code/search/subagents |
| Gemini CLI | https://github.com/google-gemini/gemini-cli | Apache-2.0; personal-account free tier upstream | large-context analysis, web/MCP/tool tasks |
| Cline | https://github.com/cline/cline | Apache-2.0; model cost separate | headless/SDK work, parallel worktrees, MCP |
| Aider | https://github.com/Aider-AI/aider | Apache-2.0; supports local models | scoped edit-test-fix loops and Git workflows |
| OpenHands | https://github.com/All-Hands-AI/OpenHands | MIT core; runtime/model separate | sandboxed software-agent experiments |
| goose | https://github.com/aaif-goose/goose | Apache-2.0; model cost separate | local workflows and MCP extensions |
| mini-swe-agent | https://github.com/SWE-agent/mini-swe-agent | MIT; model runtime separate | isolated GitHub issue-fix experiments |
| Ollama | https://github.com/ollama/ollama | MIT; local hardware | local/offline model backend |

## Reference-only / excluded

- MCP reference servers: https://github.com/modelcontextprotocol/servers — useful
  examples, but upstream explicitly treats them as reference implementations rather
  than production-ready integrations.
- Continue: https://github.com/continuedev/continue — retained as architecture and
  check-design reference because the upstream repository is read-only.
- Roo Code: https://github.com/RooCodeInc/Roo-Code — excluded from active routing
  because the official extension was shut down in May 2026.

## Routing model

The registry is intentionally fail-closed:

1. Discover only known executable names already installed on the runtime.
2. Never auto-install arbitrary packages, extensions, MCP servers, or scripts.
3. Never forward raw API keys, OAuth tokens, SSH keys, cookies, or vault values.
4. Rank assistants by explicit capability overlap and local availability.
5. Create independent workstreams for research, implementation, tests, review,
   security, documentation, and issue fixing.
6. Run mutable work only through a later CK-NEXUS sandbox/policy adapter.
7. Require normal Git diff, CI, review, and evidence checks before accepting output.

## Recommended parallel team

- **OpenCode** — primary existing-repo implementation and code search.
- **Aider** — narrow edit/test/fix lane.
- **Gemini CLI** — independent architecture/research review using its free-entry path
  when available.
- **mini-swe-agent** — issue-scoped experiment lane in an isolated worktree/container.
- **Cline or goose** — MCP/workflow lane where installed and authenticated.
- **Ollama** — local/offline inference backend for low-risk repetitive work.
- **OpenHands** — sandboxed larger autonomous tasks after resource controls are proven.

The same task should not be handed to every agent. The governor should split a task
into independent workstreams, then compare outputs. This reduces duplicated cost
and makes disagreement useful as review evidence.

## Security boundary

These assistants are **workers/providers**, never authorities. They cannot promote
Q10/Q11/Q12, merge PR #14, claim Production Ready, change frozen production
subjects, or treat their own tests as release evidence. Any future execution adapter
must preserve capability-scoped credentials, sandboxing, command restrictions,
network policy, output redaction, timeout/resource limits, and append-only evidence.

## Current V1 implementation

`creator_app/dev_assistants/registry.py` stores the curated source metadata and
lifecycle state. `creator_app/dev_assistants/orchestrator.py` discovers installed
executables and builds routing/parallel plans. It deliberately contains **no package
installer and no shell execution path**.

The next safe phase is an isolated runner adapter with one adapter per assistant,
plus CI verification that every mutation is made in a disposable worktree and
returned as a patch for CK-NEXUS review.
