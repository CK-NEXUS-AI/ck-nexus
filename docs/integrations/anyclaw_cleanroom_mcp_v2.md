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

Every tool is also annotated in MCP metadata as read-only, non-destructive, idempotent, and closed
world. These annotations are interoperability hints; CK-NEXUS policy remains the enforcement layer.

The legacy `solve_system`, unrestricted `solve_file`, unrestricted `solve_web`, provider failover, file
writes, arbitrary shell execution, credential access, and production mutation are not exposed.

## Workspace boundary

`CKNEXUS_WORKSPACE_ROOT` defines the only filesystem root visible to the clean-room solver. Requests
using absolute paths, `..`, symlinks, binary data, oversized text, sensitive credential/vault paths,
or paths outside that root fail closed. Sensitive entries are hidden from directory inventory. File
reads are UTF-8 only and credential-like values are redacted before output. Hashing is bounded and
never returns file contents.

## Exact descriptor / QR source

`creator_app.device_bridge.descriptor_generator` builds the connection descriptor directly from the
same `TOOL_SPECS` registry used by the MCP server. `creator_app.device_bridge.attestation` adds the
stronger operator path: it requires a clean Git worktree, measures exact commit and tree identities,
starts the MCP server over real stdio, asks `tools/list`, requires the live tool metadata to equal the
expected registry, and only then emits descriptor metadata.

Canonical local launch shape:

```text
python3 -m creator_app.device_bridge.mcp_server_v2
```

Measured descriptor command:

```text
uv run python scripts/generate_device_bridge_descriptor.py --workspace .
```

The generator prints canonical JSON followed by its SHA-256. QR rendering should encode only that
measured canonical JSON. Do not hand-write a QR descriptor and do not reuse a QR after the checkout,
tool registry, or source identity changes.

The connection descriptor remains untrusted metadata until CK-NEXUS verifies its command, advertised
tool registry, exact source/build identity, package policy, and evidence fingerprint.

## ChatGPT / remote boundary

Local stdio is for local trusted hosts. ChatGPT does not directly reach a developer-machine localhost
MCP server. A future remote connection must use an approved Secure MCP Tunnel or an authenticated
remote MCP endpoint; never expose the local stdio server or an unauthenticated HTTP wrapper directly
to the public Internet.

Reference: https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt

## Verification

Tests cover path traversal, absolute paths, symlink escape attempts, sensitive-path denial, secret
redaction, content-free hashing, non-executing code review, descriptor/runtime registry equality,
MCP read-only annotations, exact Git source attestation, dirty-tree denial, runtime registry-drift
denial, and a protocol-level MCP `stdio` handshake.

## Dependency note

The current locked development environment already resolves the official `mcp` package through the
existing OpenAI Agents dependency graph. A future dependency-maintenance change should declare MCP as
a direct project dependency and regenerate `uv.lock` in a controlled workspace; do not hand-edit the
lockfile.

## Promotion boundary

This V2 bridge does not grant trust to the Android app, does not access Gmail/Outlook/OpenAI/GitHub
credentials, and does not enable device or SD-card mutation. Promotion remains:

`descriptor valid -> protocol registry verified -> exact build verified -> clean-room package review ->
read-only canary -> security regression -> governance review -> trusted read-only`.

Q10/Q11/Q12 and Production status are unchanged.
