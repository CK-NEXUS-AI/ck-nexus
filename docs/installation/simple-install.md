# Simple CK-NEXUS Setup

## Why

The default path should require the fewest decisions while keeping security gates visible. Advanced deployment remains available through the existing Docker/VPS runbooks.

## Three-step flow

1. Check: `ck-nexus install` verifies local readiness and prepares the user state directory.
2. Start: `ck-nexus start` launches the local runtime in the background.
3. Ready: `ck-nexus status` reports whether the runtime is running.

Common commands:

```text
ck-nexus install
ck-nexus start
ck-nexus stop
ck-nexus status
ck-nexus help
```

The local default address is `http://127.0.0.1:8000`. The default bind remains loopback-only.

## Failure behavior

The installer fails closed when required runtime packages or minimum free disk space are missing. It prints a plain-language corrective action instead of claiming success. Start failures point to the local runtime log under the CK-NEXUS state directory.

## Compatibility

Running `ck-nexus` with no subcommand preserves the legacy foreground server behavior. The new commands are an additive interface.

## Advanced deployment

Production-like Docker, TLS, database, credentials, cgroups, and external evidence remain separate governed deployment concerns. This simple setup does not certify Production readiness and does not alter Q10/Q11/Q12 state.
