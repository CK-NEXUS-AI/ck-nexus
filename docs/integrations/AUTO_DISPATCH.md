# CK-NEXUS Auto Dispatch

## Purpose

Provide one MCP entry point for fast AI answers and development-task routing while reusing the existing CK-NEXUS provider key pool and Universal System. No additional agent framework is required.

## MCP tools

- `cknexus_auto_dispatch(request, mode="auto", priority=2, max_tokens=512)`
  - `auto`: routes development-oriented requests to the existing planning path; ordinary questions to the configured external model.
  - `answer`: calls the configured provider with bounded attempts and a short timeout.
  - `plan`: runs the existing CK-NEXUS planning path only.
- `cknexus_ai_provider_status()`: reports configured provider/model metadata and redacted health state.
- `cknexus_ai_reply(request, max_tokens=512)`: direct fast model reply.

## Important boundaries

- A plan does not execute shell commands or modify repository files.
- Provider output is untrusted and cannot authorize tools, code changes, deployments, or production mutations.
- Actual execution must go through the CK-NEXUS policy, approval, credential, sandbox, verification, and evidence chain.
- Provider health is `unknown` until measured; a configured key is not proof that the model is reachable.
- The MCP service stays bound to `127.0.0.1:8765`. Remote clients need a separately authenticated HTTPS/Secure MCP boundary; do not expose this listener directly.
- MCP server instructions recommend this dispatcher for each new request, but whether a client automatically invokes a tool depends on that client's configuration and tool policy.

## Provider environment

The service consumes the existing protected `/etc/cknexus/qwen.env` through a systemd EnvironmentFile. Secret values are not copied into source, plugin files, or evidence.

## Verification

Tests: `tests/test_mcp_auto_dispatch.py` and the focused AI-team tests. Live provider verification must be recorded separately from mocked tests. `scripts/ck-health` must run after implementation/deployment changes.
