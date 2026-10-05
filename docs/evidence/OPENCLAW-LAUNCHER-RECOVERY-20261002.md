# OpenClaw Launcher Recovery — 2026-10-02

## Evidence

On Termux/aarch64, the preserved OpenClaw 2026.9.6 package was directly executable, but `openclaw` was absent from PATH.

A user-local launcher was created at:

`~/.local/bin/openclaw`

The launcher delegates to the preserved package entrypoint and was verified in a fresh shell context:

- `command -v openclaw` -> `~/.local/bin/openclaw`
- `openclaw --version` -> `OpenClaw 2026.9.6 (eb377ac)`
- exit code: 0

No global package replacement was performed.

## Gateway

Read-only `openclaw gateway status` did not return within the bounded timeout.

A bounded `openclaw health` invocation also remained running and was terminated/expired by the process-control layer.

Therefore Gateway/health runtime readiness remains NOT VERIFIED.

## Safety

- No API keys, tokens, passwords, OTPs, or OAuth credentials were read or emitted.
- No credential registration was performed.
- No production mutation was performed.
- No GitHub merge/release/tag was performed.

## Status

Launcher: VERIFIED
Package: VERIFIED
Gateway: NOT VERIFIED
Health: NOT VERIFIED
Production: NO-GO
