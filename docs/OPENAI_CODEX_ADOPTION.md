# OpenAI Codex adoption for CK-NEXUS

Review date: 2026-08-05  
Upstream repository: `https://github.com/openai/codex`  
Reviewed shallow-clone commit: `5d89ab6`

## Relevant upstream surfaces

| Surface | Best fit | CK-NEXUS decision |
|---|---|---|
| Codex CLI / `codex exec` | Trusted local or CI engineering jobs | Adopted in v0.2 through a guarded subprocess bridge |
| Codex SDK | Typed programmatic threads and resumable automation | Recommended next step after the bridge contract stabilizes |
| `codex mcp-server` | Codex as a specialist inside an Agents SDK workflow | Recommended for a later multi-agent orchestration edition |
| `codex app-server` | Rich clients with approvals, history, auth, and streamed events | Defer until CK-NEXUS has a dedicated engineering UI |
| Rust core/TUI | Upstream runtime and terminal experience | Do not fork for the current product; maintenance cost is too high |

## What v0.2 adopts

- A separate Codex specialist runtime; Creator Agents remain on the OpenAI Agents SDK.
- Non-interactive `codex exec` with a fixed server-configured workspace.
- `read-only` default sandbox, optional `workspace-write`, and no support for
  `danger-full-access`.
- Disabled-by-default HTTP endpoint protected by the CK-NEXUS bearer token.
- Argument-safe process spawning, no shell interpolation, fixed timeout, bounded output, and
  filtering of common secret-bearing environment variables.
- Optional writable `CODEX_HOME` for containers without copying credentials from another account.

## What was intentionally not copied

The upstream repository was cloned for inspection, but no Rust core, TUI, SDK, or app-server source
was copied into CK-NEXUS. The v0.2 bridge invokes the separately installed official CLI. This keeps
upstream updates and licensing boundaries clear and avoids maintaining a long-lived Codex fork.

## Future migration path

1. Replace the subprocess adapter with the Python Codex SDK when its beta contract is acceptable
   for the product's support policy.
2. Use `codex mcp-server` when CK-NEXUS adds deterministic multi-agent engineering workflows.
3. Adopt app-server only if a dedicated UI needs streamed events, approvals, and resumable threads.

Official references:

- <https://developers.openai.com/codex/codex-sdk>
- <https://developers.openai.com/codex/mcp-server>
- <https://developers.openai.com/codex/app-server>
- <https://developers.openai.com/codex/auth>
