# CK-NEXUS OpenCode Control Bridge

Status: Post-P0 / development only. This component is not production-closure evidence and must not change Q10/Q11/Q12 state.

## Purpose

Expose a read-only MCP discovery surface to a user-owned OpenCode HTTP server. This bridge does not own CK-NEXUS permissions and cannot authorize workspace mutation.

Supported tools:

- `opencode_health` — read-only health check
- `opencode_list_sessions` — read-only session discovery
- `opencode_session_status` — read-only status check
- `opencode_get_messages` — read-only, redacted message inspection

The bridge never reads or returns provider API keys. OpenCode credentials stay in environment variables and are only used to authenticate to the local OpenCode server.

## Security model

1. The upstream URL must use a numeric loopback IP (`127.0.0.1` or `[::1]`); DNS hostnames are rejected to avoid hostname rebinding.
2. OpenCode server authentication uses `OPENCODE_SERVER_PASSWORD`.
3. The MCP bridge binds to loopback by default.
4. A non-loopback bridge bind is rejected unless `CKNEXUS_BRIDGE_TOKEN` is set.
5. This bridge exposes read-only health, session discovery, status and redacted message inspection only.
6. Prompt execution, continuation, abort and other workspace mutations are intentionally disabled until CK-NEXUS Core approval, policy and evidence integration exists.
7. Use an authenticated HTTPS tunnel to connect ChatGPT to the local MCP endpoint. Do not expose the raw OpenCode port to the public internet.
8. Secret-like fields and common token patterns are redacted from bridge responses.

## Start OpenCode headless

Use a fresh random password and keep it only in the current shell/secret manager.

```bash
export OPENCODE_SERVER_PASSWORD="$(openssl rand -hex 32)"
export OPENCODE_SERVER_USERNAME="opencode"
opencode serve --hostname 127.0.0.1 --port 18924
```

If an existing OpenCode TUI/session server is already running on another port, do not start a second server; set `OPENCODE_BASE_URL` to that server using `127.0.0.1` or `[::1]`.

## Start the MCP bridge

In a second terminal:

```bash
cd integrations/opencode-control-bridge
npm install

export OPENCODE_BASE_URL="http://127.0.0.1:18924"
export OPENCODE_SERVER_USERNAME="opencode"
export OPENCODE_SERVER_PASSWORD="<same value used by OpenCode>"
npm run typecheck
npm start
```

The bridge listens on:

```text
http://127.0.0.1:18925/mcp
```

and exposes a simple local health endpoint at `/health`.

## Connect to ChatGPT

ChatGPT cannot connect directly to a localhost MCP server. Use ChatGPT Developer Mode with a remote MCP endpoint. For a bridge on a developer machine/private network, use OpenAI Secure MCP Tunnel when available for the account/workspace rather than exposing port 18925 publicly.

After the remote MCP endpoint is available:

1. Enable ChatGPT Developer Mode.
2. Create a custom app/MCP connection.
3. Point it at the tunneled `/mcp` endpoint.
4. Scan tools and confirm the four read-only tools above.
5. Confirm only the four read-only tools are exposed. Workspace execution and mutation are not available through this bridge.

## Current closure boundary

This bridge is intentionally outside the frozen production runtime and outside release evidence. It must not be used to claim Q10 Native Codex Security PASS, Q11 PASS, Q12 PASS, Production Ready, or permission to merge PR #14.
