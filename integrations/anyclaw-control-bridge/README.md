# CK-NEXUS AnyClaw Control Bridge

Post-P0 development integration. This bridge exposes governed AnyClaw CLI capabilities as a remote HTTP MCP server for CK-NEXUS/ChatGPT.

## Security model

- CK-NEXUS remains authority; AnyClaw is an execution adapter only.
- Defaults to loopback `127.0.0.1:18926`.
- Non-loopback binding is refused unless `CKNEXUS_ANYCLAW_TOKEN` is set.
- Raw API keys/tokens/passwords must never be passed as tool arguments.
- Credential-looking arguments are rejected.
- Tool output is redacted for common credential formats.
- AnyClaw results are development/tool evidence only and cannot substitute for Native Codex Security Q10 evidence.
- Production status remains NO-GO until the canonical closure gates pass.

## Prerequisite

Install AnyClaw using its official project instructions, then verify:

```bash
anyclaw version
anyclaw list
```

AnyClaw itself can also export installed packages through stdio MCP using `anyclaw mcp`; this bridge exists to provide a governed HTTP MCP surface suitable for CK-NEXUS/ChatGPT integration and policy enforcement.

## Run locally

```bash
cd integrations/anyclaw-control-bridge
npm install
npm run typecheck
npm start
```

Defaults:

```text
MCP:    http://127.0.0.1:18926/mcp
Health: http://127.0.0.1:18926/health
```

Optional environment:

```bash
export ANYCLAW_BIN=anyclaw
export CKNEXUS_ANYCLAW_HOST=127.0.0.1
export CKNEXUS_ANYCLAW_PORT=18926
```

For a non-loopback bind, configure a strong bridge token and expose the bridge only through authenticated HTTPS/tunnel infrastructure:

```bash
export CKNEXUS_ANYCLAW_HOST=0.0.0.0
export CKNEXUS_ANYCLAW_TOKEN='set-in-secret-store-not-source-control'
```

Do not commit the token.

## Exposed tools

- `anyclaw_version`
- `anyclaw_list_installed`
- `anyclaw_search_registry`
- `anyclaw_daemon_status`
- `anyclaw_run`
- `anyclaw_install`
- `anyclaw_uninstall`

Use discovery/status tools before mutation. Install/uninstall/run remain governed actions and must not be used to bypass CK-NEXUS policy or provider restrictions.

## ChatGPT connection

Expose `http://127.0.0.1:18926/mcp` through a secure authenticated HTTPS MCP tunnel/endpoint, then add that remote MCP URL as a custom ChatGPT app/connector in Developer Mode. Do not expose the local port directly to the public internet.
