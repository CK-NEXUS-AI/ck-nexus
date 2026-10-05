# CK-NEXUS / OpenClaw Runtime Discovery — 2026-10-02

## Evidence status

- Collection mode: read-only
- Runtime device: `localhost` (Desktop Commander)
- Device ID: `5f5d5802-7451-4427-b623-4089c675717d`
- Host: Android 12 / aarch64
- Node: v24.18.0
- npm: 11.20.0
- VPS `10616a96dd5c121bb`: OFFLINE
- OpenClaw in PATH: NOT FOUND
- Gateway 18789: NOT VERIFIED / no listener observed
- CDP 18800: NOT VERIFIED / no listener observed

## OpenClaw package evidence

A preserved OpenClaw 2026.9.6 package was found at:

`~/.openclaw-termux-fix-20261001-215101/openclaw-package-backup/`

Direct execution of its launcher was successful:

- `node openclaw.mjs --version` => `OpenClaw 2026.9.6 (eb377ac)`, exit 0
- `node openclaw.mjs --help` => exit 0
- package engine: `>=24.16.0 <25 || >=26.1.0`
- bin: `openclaw -> openclaw.mjs`

This proves the preserved package can start under the current Node runtime. It does NOT prove the normal `openclaw` command is installed in PATH or that the Gateway is running.

## Installed/static capability evidence

The preserved package contains 51 top-level skill directories. Examples include:

- coding-agent
- github
- gemini
- notion
- mcporter
- tmux
- taskflow
- node-connect
- healthcheck
- skill-creator
- weather
- xurl

The package source/docs also expose mutation-capable surfaces including:

- exec / process
- browser
- MCP
- plugins
- skills
- message/channel actions
- scheduling/cron
- web_search/web_fetch
- agent/sub-agent execution
- filesystem/network access through runtime capabilities

Static source evidence also documents process-level proxy coverage for common Node HTTP/WebSocket clients, while explicitly noting that this is NOT an OS-level network sandbox. Therefore network coverage remains a CK-NEXUS governance question rather than being assumed solved.

## CK-NEXUS mutation-surface interpretation

No runtime evidence was collected that proves universal mediation of S01-S14. Therefore all 14 surfaces remain UNKNOWN for coverage purposes.

Unknown is not safe.

The correct next runtime tests, once the package is made reachable through the normal launcher, are bounded read-only/deny-first checks for:

S01 exec, S02 process, S03 browser, S04 MCP, S05 filesystem, S06 network, S07 plugin, S08 skill, S09 sub-agent, S10 credentials, S11 device/node, S12 message, S13 web_search, S14 scheduling.

Composite paths C1-C5 remain INCOMPLETE until downstream mutation leaves are demonstrated to pass through an enforceable decision boundary.

## Security boundary

No credential values, OAuth tokens, API keys, or gateway token values were read or emitted.

No OpenClaw setup, onboarding, configuration mutation, credential registration, OAuth authorization, production mutation, Git merge, or release was performed.

## GitHub verification context

PR #261 remains OPEN + DRAFT + NOT MERGED.

Current head:
`54087b62409ad351b51cfabc32ad64323b146724`

The PR currently has no reported combined status entries through the connected GitHub status API, and SonarQube Cloud has reported that its last analysis failed.

## Verdict

RUNTIME PACKAGE: VERIFIED
NORMAL CLI PATH: NOT VERIFIED
GATEWAY: NOT VERIFIED
MUTATION COVERAGE: UNKNOWN
P0.1 GATEWAY: DESIGNED
P0.2 SCANNER: DESIGNED
PRODUCTION: NO-GO
