# CK-NEXUS OpenCode Control Bridge

Status: Post-P0 / development only. This component is not production-closure evidence and must not change Q10/Q11/Q12 state.

## Purpose

Expose a small, governed MCP tool surface from ChatGPT/CK-NEXUS to a user-owned OpenCode HTTP server without exposing OpenCode credentials to agents or repository state.

Supported tools:

- `opencode_health` — read-only health check
- `opencode_list_sessions` — read-only session discovery
- `opencode_session_status` — read-only status check
- `opencode_get_messages` — read-only, redacted message inspection
- `opencode_run_prompt` — asynchronous task handoff
- `opencode_continue_cknexus` — fixed governed continuation prompt for pending CK-NEXUS work
- `opencode_abort_session` — stop a running session

The bridge never reads or returns provider API keys. OpenCode credentials stay in environment variables and are only used to authenticate to the local OpenCode server.

## Security model

1. OpenCode binds to loopback only.
2. OpenCode server authentication uses `OPENCODE_SERVER_PASSWORD`.
3. The MCP bridge binds to loopback by default.
4. A non-loopback bridge bind is rejected unless `CKNEXUS_BRIDGE_TOKEN` is set.
5. Use an OpenAI-supported Secure MCP Tunnel or another authenticated HTTPS boundary to connect ChatGPT to the local MCP endpoint. Do not expose the raw OpenCode port to the public internet.
6. Mutating MCP actions are annotated as write/open-world actions. ChatGPT permissions remain an independent control layer.
7. Secret-like fields and common token patterns are redacted from bridge responses.

## Start OpenCode headless

Use a fresh random password and keep it only in the current shell/secret manager.

```bash
export OPENCODE_SERVER_PASSWORD="$(openssl rand -hex 32)"
export OPENCODE_SERVER_USERNAME="opencode"
opencode serve --hostname 127.0.0.1 --port 18924
```

If an existing OpenCode TUI/session server is already running on another port, do not start a second server; set `OPENCODE_BASE_URL` to that server instead.

## Start the MCP bridge

In a second terminal:

```bash
cd integrations/opencode-control-bridge
npm install

export OPENCODE_BASE_URL="http://127.0.0.1:18924"
export OPENCODE_SERVER_USERNAME="opencode"
export OPENCODE_SERVER_PASSWORD="<same value used by OpenCode>"
export OPENCODE_SESSION_ID="ses_0118776b6ffeORNKewNaFzbtWH"
export CKNEXUS_AUTOSTART="true"

npm run typecheck
npm start
```

The bridge listens on:

```text
http://127.0.0.1:18925/mcp
```

and exposes a simple local health endpoint at `/health`.

## Automatic continuation

When `CKNEXUS_AUTOSTART=true` and `OPENCODE_SESSION_ID` is configured, bridge startup will:

1. verify OpenCode `/global/health`;
2. send exactly one governed asynchronous continuation prompt to the configured session;
3. persist only the session ID, prompt digest, timestamp, and `production_status=NO-GO` in `.opencode-bridge-state.json`;
4. retry every 15 seconds only until the first successful handoff;
5. refuse to treat the handoff as production evidence.

The fixed continuation contract includes:

- latest exact GitHub evidence wins;
- no fabricated evidence;
- no secret exposure;
- no gate weakening;
- no PR #14 merge;
- frozen target exact-subject checks;
- Production remains NO-GO until real Q10 → Q11 → Q12 → provenance → Final Production Package closure.

## Connect to ChatGPT

ChatGPT cannot connect directly to a localhost MCP server. Use ChatGPT Developer Mode with a remote MCP endpoint. For a bridge on a developer machine/private network, use OpenAI Secure MCP Tunnel when available for the account/workspace rather than exposing port 18925 publicly.

After the remote MCP endpoint is available:

1. Enable ChatGPT Developer Mode.
2. Create a custom app/MCP connection.
3. Point it at the tunneled `/mcp` endpoint.
4. Scan tools and confirm the seven tools above.
5. Keep write actions governed by ChatGPT app permissions.
6. In this CK-NEXUS chat, call `opencode_health`, then `opencode_session_status`, then `opencode_continue_cknexus` when continuation is required.

## Current closure boundary

This bridge is intentionally outside the frozen production runtime and outside release evidence. It must not be used to claim Q10 Native Codex Security PASS, Q11 PASS, Q12 PASS, Production Ready, or permission to merge PR #14.
