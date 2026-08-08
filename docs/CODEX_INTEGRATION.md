# CK-NEXUS Codex Bridge

CK-NEXUS v0.2 adds an optional local bridge to OpenAI Codex CLI for trusted software-engineering
tasks. Creator Agents continue to use the OpenAI Agents SDK; Codex is a separate specialist and is
disabled by default.

## Why the bridge is separate

- Creator Agents generate content through the Agents SDK.
- Codex works inside a source workspace and can inspect or edit code.
- Keeping separate runtimes makes permissions, audit boundaries, and failure modes explicit.

## Install and authenticate Codex CLI

Install the official CLI:

```bash
npm install -g @openai/codex
codex login
codex login status
```

For a project-local install, run:

```bash
npm install --prefix .tools/codex @openai/codex
export CKNEXUS_CODEX_BIN="$PWD/.tools/codex/node_modules/.bin/codex"
```

Codex supports ChatGPT sign-in for subscription access or API-key authentication for usage-based
access. Do not paste credentials into CK-NEXUS requests or commit them to the repository.

## Enable the bridge

Set a strong server access token before enabling the endpoint:

```dotenv
CKNEXUS_ACCESS_TOKEN=<strong-random-value>
CKNEXUS_CODEX_ENABLED=true
CKNEXUS_CODEX_BIN=codex
CKNEXUS_CODEX_HOME=/absolute/writable/path/to/codex-home
CKNEXUS_CODEX_WORKSPACE=/absolute/path/to/trusted/repository
CKNEXUS_CODEX_SANDBOX=read-only
```

Use `workspace-write` only when CK-NEXUS should allow Codex to modify the configured repository.
The bridge rejects `danger-full-access`, never accepts a working directory from an HTTP request,
uses argument-safe process execution without a shell, strips common secret-bearing environment
variables, applies a timeout, and caps returned output.

## API

- `GET /api/codex/status` reports configuration readiness without exposing credentials.
- `POST /api/codex/tasks` accepts `{ "prompt": "..." }` and requires the bearer token.

Example:

```bash
curl http://127.0.0.1:8000/api/codex/tasks \
  -H "Authorization: Bearer $CKNEXUS_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Review the tests and suggest the smallest safe improvement."}'
```

Keep the service bound to localhost unless it is placed behind HTTPS, strong authentication,
network controls, rate limits, and an audit layer. Never expose this endpoint as an unrestricted
public coding service.

In a container, `CKNEXUS_CODEX_HOME` must point to a writable persistent directory. Authenticate
that same directory once with `CODEX_HOME=/path codex login`; do not copy credential files from a
different account or machine.
