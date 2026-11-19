# AI Fast Path: Automatic Tool Routing

## Objective

Minimize wall-clock time for each @ai request by selecting the smallest set of tools that can complete it, running independent read-only work concurrently, and verifying results from the system that owns the state.

This is a routing policy, not permission to invoke every available tool indiscriminately. Unrelated calls increase latency, consume provider credits, widen the data exposure surface, and can trigger unintended side effects.

## Default request lifecycle

1. Classify the request: answer/research, repository change, remote operation, file work, connected-app action, or scheduled automation.
2. Discover only relevant capabilities from connected ChatGPT tools, CK-NEXUS MCP, and local/VPS tools. Cache capability inventory for the current task; re-probe only when connection or permissions may have changed.
3. Batch independent read-only probes with parallel tool calls (repository status, service health, tests metadata, agent session status). Do not parallelize conflicting writes to the same file or service.
4. Plan briefly for multi-step changes. Inspect project instructions, dirty worktree, and tests before editing.
5. Execute in the closest authoritative environment: repository edits in /root/ck-nexus; Termux issues on the Android/Termux device; VPS services on the VPS; connected apps through their own connector.
6. Delegate selectively. Use already-running/linked agents first. Managed agents that spend wallet credits require explicit user choice/confirmation; do not start them just to appear parallel.
7. Bound every execution with timeouts, concurrency caps, retry limits, allowed paths, and a clear stop condition.
8. Verify from real outputs: tests, lint, health, service status, and a live canary where safe. A plan is not execution; execution is not verification.
9. Return a concise report: changed items, verified results, remaining blockers, evidence path.

## Routing matrix

| Request type | Primary tools | Parallelizable checks | Gate |
|---|---|---|---|
| CK-NEXUS code | Remote Desktop Commander + repo scripts + existing test runner | Git status, instruction discovery, targeted test discovery | Preserve all pre-existing changes; no commit/push unless requested |
| VPS incident | Remote Desktop Commander + systemd/Docker/CK health | service status, disk, logs, container health | No public bind, destructive cleanup, or unbounded restart |
| Termux/OpenClaw | Termux device + bounded CLI probes + MCP tunnel | version, temp/log permissions, tunnel, process state | Do not claim OpenClaw works until a real MCP call succeeds |
| MCP integration | MCP initialize/tools/list/call + service logs | protocol checks and loopback bind | Authentication and loopback-only boundary remain enabled |
| Research/docs | Web search + Context7 + source files | independent sources/docs | Cite external claims; do not install tools merely because they exist |
| GitHub work | GitHub connector + repository state | issue/PR read, commit comparison | No push, merge, or public write unless requested |
| Other connected apps | Their dedicated connector | independent metadata/read calls | External sends, purchases, deletes, credential changes require explicit approval |
| Multi-agent coding | Existing TeamDirector / already-connected agent sessions | research/review on isolated scopes | No wallet-billed managed agent without explicit confirmation |

## Parallel execution rules

- Parallelize independent reads and independent review/research tasks.
- For edits, use distinct files or isolated worktrees. Never have multiple writers patch the same file concurrently.
- Set a small default concurrency (2–4); raise only when resource headroom is demonstrated.
- Use short per-command timeouts and poll existing process IDs rather than launching duplicate jobs.
- Avoid repeated full test-suite runs while a previous run is active. Run focused tests first, then one full suite.
- Avoid polling every service and tool on every turn; recheck only capabilities relevant to the current request.
- On timeout, inspect the process and logs before retrying; do not blindly launch a second copy.
- Record redacted evidence and checksums for substantive changes.

## Safety and authority boundaries

- unknown_tool=deny; do not infer capabilities from names.
- Secrets never enter transcripts, logs, command output, or evidence.
- PLANNED_NOT_EXECUTED remains non-mutating.
- Production deployment, external messages, financial actions, destructive operations, credential rotation, and irreversible Git operations remain approval-gated.
- @ai means automatic routing and execution of authorized work, not blanket approval for every possible side effect.
- ChatGPT connector availability is not proof that the same connector is installed on the VPS or Termux.
- Background continuation requires a real scheduler/automation; this policy alone does not create an always-running agent.

## Current environment notes (observed 2026-10-22)

- Desktop Commander devices localhost (Termux) and vps3680569.trouble-free.net were both listed online during discovery; mobile connectivity may fluctuate.
- CK-NEXUS MCP, API Gateway, Scanner, and Watchdog timer were active on the VPS; MCP remained bound to 127.0.0.1:8765.
- Root filesystem was 91% used (about 3.9 GiB free). Avoid installing large frameworks until disk cleanup is reviewed safely.
- OpenCode, Gemini CLI, and Claude CLI were present on the VPS. Their presence does not prove provider access or successful execution.
- No online CodeAgent sessions were found. Managed agents are available but use the CodeAgent wallet; do not launch them automatically.
- OpenClaw CLI exists on Termux and returned a version, but a bounded gateway-status probe remained running and native MCP tool-list invocation returned HTTP 400 in the first probe. OpenClaw is not yet verified as a functioning autonomous gateway; inspect session/protocol handling and startup logs before retrying.