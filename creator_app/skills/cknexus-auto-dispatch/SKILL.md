---
name: cknexus-auto-dispatch
version: 1.1.0
description: Route each request to the CK-NEXUS fast AI reply or governed development workflow, using existing tools before adding dependencies.
---

# CK-NEXUS Auto Dispatch

Use this workflow at the beginning of each user request when the CK-NEXUS MCP tool is available. See docs/integrations/AI_FAST_PATH.md for the full routing and performance policy.

## Fast dispatch
1. Classify the request and select only relevant tools; do not invoke unrelated tools just to invoke everything.
2. Batch independent read-only probes concurrently. Cache discovery within the task and re-probe only when state, connection, or permissions may have changed.
3. If cknexus_auto_dispatch is available, call it with the original request and mode=auto.
4. For ordinary questions, use the configured model answer path. If the provider is unavailable, report the exact safe error code and continue with other available assistant capabilities without pretending a model call succeeded.
5. For repository/code/development requests, use the CK-NEXUS control-plane graph first. PLANNED_NOT_EXECUTED is not code execution, verification, or production evidence.
6. Use existing MCP, repository, Git, sandbox, test, and health tools before suggesting or installing another framework.
7. Parallelize only independent read/research/review tasks. Give each writer an isolated workspace or distinct file scope.
8. Keep execution bounded by timeouts, concurrency caps, retry limits, and allowed paths. Poll existing process IDs after timeouts; do not launch duplicate jobs blindly.
9. Preserve all existing uncommitted work. Never run destructive Git commands or silently overwrite unrelated files.
10. Keep secrets out of prompts, output, shell history, logs, and evidence. Report provider/model names and status only.
11. For code changes, inspect project rules and Git state, make the smallest patch, run focused tests before one full suite, then lint/security/health checks and redacted evidence with checksums.
12. Distinguish PLANNED_NOT_EXECUTED, EXECUTED, VERIFIED, and PRODUCTION. Never claim one state based on another.

## Delegation
- Prefer already-running and linked agent sessions.
- Do not launch wallet-billed managed agents unless the user explicitly approves their use and cost.
- ChatGPT connectors, VPS tools, and Termux tools are separate capabilities; verify the target-side connection before assuming cross-environment access.

## Safety
- unknown tools/workflows are denied by default.
- Production deployment, external sends, destructive operations, credential rotation, and irreversible Git operations remain approval-gated.
- MCP must remain authenticated and loopback-only unless a separately reviewed secure transport is configured.
- This skill does not create an always-running background process; scheduled work requires an actual automation/scheduler.

## If CK-NEXUS MCP is not connected
- Do not assume the loopback-only VPS MCP endpoint is reachable from another device.
- Do not expose port 8765 publicly or disable authorization to make it connect.
- Use the already-connected Remote Desktop Commander only for actions it actually supports.
- State that auto-dispatch is not connected in that client, and continue safe work through available tools.