# AnyClaw clean-room MCP V2

Status: development/security hardening only. The Android package `gptos.intelligence.assistant`
remains quarantined and is not used as a trust root or execution dependency.

## Design

The V2 bridge runs from canonical CK-NEXUS source and uses the official MCP Python SDK `FastMCP`
with local `stdio` transport. The MCP server does not import or call the quarantined AnyClaw Android
runtime. It exposes a deliberately narrow read-only tool set:

- `bridge_status`
- `workspace_list`
- `workspace_read_text`
- `workspace_sha256`
- `solve_data_json`
- `solve_code_review`

The legacy `solve_system`, unrestricted `solve_file`, unrestricted `solve_web`, provider failover, file
writes, arbitrary shell execution, credential access, and production mutation are not exposed.

## Workspace boundary

`CKNEXUS_WORKSPACE_ROOT` defines the only filesystem root visible to the clean-room solver. Requests
using absolute paths, `..`, symlinks, binary data, oversized text, or paths outside that root fail
closed. File reads are UTF-8 only and credential-like values are redacted before output. Hashing is
bounded and never returns file contents.

## Exact descriptor / QR source

`creator_app.device_bridge.descriptor_generator` builds the connection descriptor directly from the
same `TOOL_SPECS` registry used by the MCP server. The payload includes the exact source commit and a
registry SHA-256. A QR renderer may encode that canonical JSON only after the checkout and runtime
registry have been independently verified.

Canonical local launch shape:

```text
python3 -m creator_app.device_bridge.mcp_server_v2
```

The connection descriptor remains untrusted metadata until CK-NEXUS verifies its command, advertised
tool registry, exact source/build identity, package policy, and evidence fingerprint.

## Verification

Tests cover path traversal, absolute paths, symlink escape attempts, secret redaction, content-free
hashing, non-executing code review, descriptor/runtime registry equality, and a protocol-level MCP
`stdio` handshake that lists the exact server tool set.

## Dependency note

The current locked development environment already resolves the official `mcp` package through the
existing OpenAI Agents dependency graph. A future dependency-maintenance change should declare MCP as
a direct project dependency and regenerate `uv.lock` in a controlled workspace; this V2 security PR
does not hand-edit the lockfile.

## Promotion boundary

This V2 bridge does not grant trust to the Android app, does not access Gmail/Outlook/OpenAI/GitHub
credentials, and does not enable device or SD-card mutation. Promotion remains:

`descriptor valid -> protocol registry verified -> exact build verified -> clean-room package review ->
read-only canary -> security regression -> governance review -> trusted read-only`.

Q10/Q11/Q12 and Production status are unchanged.
