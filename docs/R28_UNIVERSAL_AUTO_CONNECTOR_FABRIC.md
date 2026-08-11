# R28 Universal Auto Connector Fabric

Status: DEVELOPMENT CANDIDATE — not Production Ready.

## Purpose

R28 adds a model-neutral connector control plane. A connector is never trusted merely because an endpoint responds. The lifecycle is:

REGISTER -> DISCOVER -> SCHEMA_VERIFIED -> ACTIVATE_READ_ONLY / ACTIVATE_WRITE -> POLICY AUTHORIZATION -> EXECUTE -> EVIDENCE

## Protocol support

- MCP protocol target: 2026-07-28 stateless HTTP core.
- OpenAPI: 3.x JSON documents, with optional YAML parsing only when PyYAML is already installed.
- No OpenAPI execution path is enabled in this release; OpenAPI is discovery/normalization/binding only.
- MCP execution exists internally but defaults to `FailClosedAuthorizer`; the public API deliberately exposes no execute endpoint until CK Policy Authority is wired into this path.

## Security invariants

1. HTTPS is required for remote endpoints. HTTP is allowed only when `allow_private_network=true`, intended for explicitly trusted local/test networks.
2. URLs containing username/password, query strings, or fragments are rejected.
3. Public-mode DNS resolution rejects non-global addresses to reduce SSRF exposure.
4. HTTP redirects are not followed by the default transport.
5. Responses and schemas are size-bounded.
6. MCP tool names and `inputSchema` are validated; malformed `x-mcp-header` declarations reject only that tool.
7. External JSON Schema `$ref` values are not auto-dereferenced.
8. Tool annotations are treated as advisory. Read-only classification is conservative.
9. Registry files store credential references, never raw credential values.
10. MCP bearer tokens are resolved at call time through the existing Credential Broker for known credential references.
11. Evidence is written to a hash-chained JSONL ledger.
12. Write/destructive tools are never auto-activated by registration.

## API

When `CKNEXUS_CONNECTOR_FABRIC_ENABLED=true`:

- `GET /api/connectors`
- `POST /api/connectors`
- `POST /api/connectors/{connector_id}/discover`
- `POST /api/connectors/{connector_id}/activate`
- `GET /api/connectors/{connector_id}/tools`

All endpoints inherit CK-NEXUS access-token protection. There is intentionally no public connector execution endpoint in R28.

## Model binding

Model-facing logical tool names are namespaced as:

`<connector_id>.<tool_name>`

This avoids collisions when multiple MCP/OpenAPI servers expose the same native tool name.

In read-only activation mode, only tools classified `READ_ONLY` are exposed to model routing. `WRITE`, `DESTRUCTIVE`, and `UNKNOWN` remain withheld.

## Remaining production gates

- Bind `ToolAuthorizer` to CK Capability Policy Authority signed execution grants.
- Add OAuth/CIMD authorization discovery and issuer/audience validation for arbitrary MCP servers.
- Add DNS pinning/rebinding-resistant outbound transport or controlled egress proxy.
- Validate output schemas for structured MCP results.
- Add OpenAPI execution adapter with explicit origin allowlist and Credential Broker binding.
- Staging test against at least one real MCP 2026-07-28 server.
- Staging test against a real OpenAPI provider.
- Threat model / security scan / clean-machine deployment evidence.
