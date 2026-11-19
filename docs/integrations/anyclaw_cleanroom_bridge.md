# AnyClaw clean-room bridge

Status: development only. The Android package `gptos.intelligence.assistant` remains quarantined.

## Current QR observation

The user-supplied QR advertises a local stdio descriptor for `AnyClaw AI` version `2.0`.
It points to `creator_app/anyclaw/mcp_server_secure.py` and advertises ten tools.
A QR descriptor is untrusted metadata, not proof that a protocol server is running or that its tool
registry matches the descriptor.

CK-NEXUS therefore validates connection descriptors before any device bridge can become trusted:

1. JSON size and shape are bounded.
2. Tool names are unique and syntactically constrained.
3. Only local `stdio` is accepted by this Phase-1 gate.
4. The command is parsed as argv, not executed through a shell.
5. Only a Python interpreter plus a relative `creator_app/*.py` script is accepted.
6. The advertised tool set must exactly equal the independently observed runtime registry.
7. A stable SHA-256 fingerprint is produced for evidence and QR drift detection.
8. Package/build trust is evaluated separately from descriptor validity.

## Quarantine boundary

The package `gptos.intelligence.assistant` is denied even for read-only bridging while Issue #76 is
open. A claim that the build is safe is not sufficient. Trust promotion requires independent evidence
for the exact installed APK/build, including package version, APK hash, signing certificate, dependency
provenance, outbound network behavior, and clean-room testing.

No CK-NEXUS, Gmail, Outlook, OpenAI, GitHub, device-storage, or SD-card credentials/data should be
routed through a quarantined package.

## Problem Solver boundary

Do not expose arbitrary shell execution, unrestricted file read/write, or unrestricted URL fetching as
MCP tools. A future safe Problem Solver must use capability-scoped operations:

- argv-only command execution with executable/subcommand allowlists;
- workspace-root path confinement and read-only defaults;
- explicit approval for writes or destructive actions;
- SSRF-safe outbound networking with destination policy;
- bounded input/output size, timeouts, and resource ceilings;
- secret redaction and evidence identifiers on every invocation.

## Promotion path

`descriptor_valid` -> `runtime_registry_match` -> `exact_build_verified` -> `read_only_canary` ->
`security_regression` -> `governance_review` -> `trusted_read_only`.

Mutation, credential access, and production capabilities are separate gates and are denied by this V1
policy.

This work does not satisfy Q10/Q11/Q12 and does not change Production NO-GO.
