# CK-NEXUS Buyer Handoff — Development Preview

## Product classification

This handoff is for a **Development Preview**.

Production certification is not included in this package.

## Current buyer-facing capabilities

1. CK-NEXUS runtime can run on a Windows VPS in development mode.
2. The runtime exposes a local API at `127.0.0.1:8000`.
3. Runtime status confirms mock mode, database readiness, and access-token enforcement.
4. Telegram control bridge is implemented with fail-closed behavior.
5. Telegram supports a safe bootstrap command `/whoami` before allowlist approval.
6. Read-only commands `/status` and `/health` are available after allowlist approval.
7. `/ask <text>` routes through CK-NEXUS and requires the worker access token.
8. Development CI verifies compile, Ruff, Bandit, secret scan, portable regression, and provenance classification for development scope.

## Security model

- No Telegram token is committed to source control.
- Token must be regenerated and entered directly on the VPS by the owner.
- Telegram bridge requires a verification marker before it starts.
- Token enrollment calls Telegram `getMe` before authorization.
- Telegram chat IDs are explicitly allowlisted.
- Unknown chats are blocked.
- Destructive/admin/merge/deploy commands are not available through the Telegram bridge.
- The development runtime is separate from production approval.

## Buyer installation outline

1. Provision a Windows VPS.
2. Install Node.js, Python 3.12, uv, MinGit, and Remote Desktop Commander.
3. Checkout CK-NEXUS development branch.
4. Run frozen dependency sync.
5. Create local CK-NEXUS access token on the VPS.
6. Start CK-NEXUS development runtime.
7. Regenerate a Telegram BotFather token.
8. Enter the token on the VPS using `windows_telegram_secret_enroll.ps1`.
9. Send `/whoami` to the bot.
10. Put the returned chat ID into the allowlist.
11. Test `/status`, `/health`, and `/ask`.

## Required disclosure

Tell buyers:

> This is a development preview. It demonstrates the architecture and working control surfaces, but production approval requires completion of Q10, Q11, Q12, provenance reconciliation, and final checksummed package evidence.

## Commercial suggestion

Recommended initial sale structure:

- 50% deposit to install/customize.
- 50% after buyer confirms demo acceptance.
- Production certification billed separately as a security and deployment phase.

## Acceptance test for this preview

Buyer acceptance is complete when:

- VPS runtime responds to `/api/status`.
- Authenticated runtime smoke passes.
- Telegram `/whoami` returns chat ID.
- Allowlisted Telegram `/status` and `/health` return CK-NEXUS state.
- Telegram `/ask` returns a mock-mode CK-NEXUS response.
- Buyer acknowledges this is not production-certified yet.
