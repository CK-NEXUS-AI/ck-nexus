from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from creator_app.connector_fabric.evidence import sha256_json
from creator_app.connector_fabric.models import ConnectorConfig, ConnectorProtocol, DiscoverySnapshot, NormalizedTool
from creator_app.connector_fabric.risk import classify_mcp_tool
from creator_app.connector_fabric.security import EndpointPolicy, encode_mcp_header_value, validate_endpoint, validate_x_mcp_headers
from creator_app.connector_fabric.transport import HttpTransport, UrllibHttpTransport


MCP_PROTOCOL_VERSION = "2026-07-28"
_TOOL_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
CredentialResolver = Callable[[str, str], str | None]


class MCPDiscoveryError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class MCPClient:
    """Minimal stateless MCP 2026-07-28 client for discovery and gated tool calls."""

    def __init__(
        self,
        *,
        transport: HttpTransport | None = None,
        credential_resolver: CredentialResolver | None = None,
        timeout_seconds: float = 8.0,
        max_pages: int = 100,
        max_items: int = 5_000,
        client_name: str = "ck-nexus",
        client_version: str = "0.2.0",
    ) -> None:
        self.transport = transport or UrllibHttpTransport()
        self.credential_resolver = credential_resolver
        self.timeout_seconds = timeout_seconds
        self.max_pages = max_pages
        self.max_items = max_items
        self.client_name = client_name
        self.client_version = client_version
        self._request_id = 0

    def discover(self, config: ConnectorConfig) -> DiscoverySnapshot:
        if config.protocol is not ConnectorProtocol.MCP:
            raise ValueError("MCP client received a non-MCP connector")
        validate_endpoint(
            config.url,
            policy=EndpointPolicy(allow_private_network=config.allow_private_network),
        )

        capabilities: dict[str, Any] = {}
        protocol_version = MCP_PROTOCOL_VERSION
        discovered = self._rpc(config, "server/discover", {})
        capabilities = discovered.get("capabilities", {}) if isinstance(discovered, dict) else {}
        versions = discovered.get("supportedVersions", []) if isinstance(discovered, dict) else []
        if not isinstance(versions, list) or MCP_PROTOCOL_VERSION not in versions:
            raise MCPDiscoveryError("PROTOCOL_VERSION", "MCP server does not advertise the required protocol version.")

        raw_tools, tool_cache = self._list_all(config, "tools/list", "tools")
        raw_resources, resource_cache = self._list_all(config, "resources/list", "resources", tolerate_method_not_found=True)
        raw_prompts, prompt_cache = self._list_all(config, "prompts/list", "prompts", tolerate_method_not_found=True)

        normalized: list[NormalizedTool] = []
        rejected: list[dict[str, str]] = []
        allowed = set(config.allowed_tools)
        for raw in raw_tools:
            try:
                tool = self._normalize_tool(config.connector_id, raw)
                if allowed and tool.name not in allowed:
                    continue
                normalized.append(tool)
            except ValueError as exc:
                rejected.append({"name": str(raw.get("name", "<unknown>")), "reason": str(exc)})

        normalized.sort(key=lambda item: item.name)
        payload_for_hash = {
            "protocolVersion": protocol_version,
            "capabilities": capabilities,
            "tools": [tool.as_dict() for tool in normalized],
            "resources": raw_resources,
            "prompts": raw_prompts,
        }
        ttl_candidates = [item[0] for item in (tool_cache, resource_cache, prompt_cache) if item[0] is not None]
        scopes = [item[1] for item in (tool_cache, resource_cache, prompt_cache) if item[1]]
        return DiscoverySnapshot(
            connector_id=config.connector_id,
            protocol=ConnectorProtocol.MCP,
            protocol_version=protocol_version,
            tools=tuple(normalized),
            resources=tuple(raw_resources),
            prompts=tuple(raw_prompts),
            capabilities=capabilities,
            schema_hash=sha256_json(payload_for_hash),
            cache_ttl_ms=min(ttl_candidates) if ttl_candidates else None,
            cache_scope="private" if "private" in scopes else (scopes[0] if scopes else None),
            rejected_tools=tuple(rejected),
        )

    def call_tool(self, config: ConnectorConfig, tool: NormalizedTool, arguments: dict[str, Any]) -> dict[str, Any]:
        validate_endpoint(
            config.url,
            policy=EndpointPolicy(allow_private_network=config.allow_private_network),
        )
        validate_x_mcp_headers(tool.input_schema)
        result = self._rpc(config, "tools/call", {"name": tool.name, "arguments": arguments}, name=tool.name)
        if not isinstance(result, dict):
            raise MCPDiscoveryError("BAD_RESULT", "MCP tool returned a malformed result.")
        return result

    def _list_all(
        self,
        config: ConnectorConfig,
        method: str,
        key: str,
        *,
        tolerate_method_not_found: bool = False,
    ) -> tuple[list[dict[str, Any]], tuple[int | None, str | None]]:
        cursor: str | None = None
        items: list[dict[str, Any]] = []
        ttl_ms: int | None = None
        cache_scope: str | None = None
        for _ in range(self.max_pages):
            params: dict[str, Any] = {}
            if cursor:
                params["cursor"] = cursor
            try:
                result = self._rpc(config, method, params)
            except MCPDiscoveryError as exc:
                if tolerate_method_not_found and exc.code == "METHOD_NOT_FOUND":
                    return [], (None, None)
                raise
            raw_items = result.get(key, []) if isinstance(result, dict) else []
            if not isinstance(raw_items, list):
                raise MCPDiscoveryError("BAD_RESULT", f"{method} returned malformed {key}.")
            for item in raw_items:
                if isinstance(item, dict):
                    items.append(item)
            if len(items) > self.max_items:
                raise MCPDiscoveryError("TOO_MANY_ITEMS", "MCP discovery exceeded item safety limit.")
            if isinstance(result, dict):
                value = result.get("ttlMs")
                if isinstance(value, int) and value >= 0:
                    ttl_ms = value if ttl_ms is None else min(ttl_ms, value)
                scope = result.get("cacheScope")
                if isinstance(scope, str):
                    cache_scope = scope
                next_cursor = result.get("nextCursor")
            else:
                next_cursor = None
            if not isinstance(next_cursor, str) or not next_cursor:
                return items, (ttl_ms, cache_scope)
            cursor = next_cursor
        raise MCPDiscoveryError("PAGINATION_LIMIT", "MCP discovery exceeded pagination safety limit.")

    def _rpc(
        self,
        config: ConnectorConfig,
        method: str,
        params: dict[str, Any],
        *,
        name: str | None = None,
    ) -> dict[str, Any]:
        validate_endpoint(
            config.url,
            policy=EndpointPolicy(allow_private_network=config.allow_private_network),
        )
        self._request_id += 1
        request_params = dict(params)
        request_params["_meta"] = {
            "io.modelcontextprotocol/protocolVersion": MCP_PROTOCOL_VERSION,
            "io.modelcontextprotocol/clientInfo": {"name": self.client_name, "version": self.client_version},
            "io.modelcontextprotocol/clientCapabilities": {},
        }
        payload = {"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": request_params}
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            "Mcp-Method": method,
        }
        if name is not None:
            headers["Mcp-Name"] = encode_mcp_header_value(name)
        token = self._resolve_token(config)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self.transport.request(
            "POST",
            config.url,
            headers=headers,
            body=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            timeout=self.timeout_seconds,
        )
        if response.status == 401:
            raise MCPDiscoveryError("AUTH_REQUIRED", "MCP server requires authorization.")
        if response.status == 403:
            raise MCPDiscoveryError("AUTH_DENIED", "MCP authorization was insufficient.")
        if not 200 <= response.status < 300:
            raise MCPDiscoveryError("HTTP_ERROR", f"MCP server returned HTTP {response.status}.")
        envelope = self._decode_envelope(response.body, response.headers)
        if not isinstance(envelope, dict) or envelope.get("jsonrpc") != "2.0":
            raise MCPDiscoveryError("BAD_ENVELOPE", "MCP server returned an invalid JSON-RPC envelope.")
        error = envelope.get("error")
        if isinstance(error, dict):
            code = error.get("code")
            if code == -32601:
                raise MCPDiscoveryError("METHOD_NOT_FOUND", "MCP method is not supported.")
            raise MCPDiscoveryError("RPC_ERROR", "MCP server returned a protocol error.")
        result = envelope.get("result")
        if not isinstance(result, dict):
            raise MCPDiscoveryError("BAD_RESULT", "MCP response did not contain an object result.")
        result_type = result.get("resultType")
        if result_type != "complete":
            raise MCPDiscoveryError("INPUT_REQUIRED", "MCP request requires additional input and was not auto-approved.")
        return result


    @staticmethod
    def _decode_envelope(body: bytes, headers: Any) -> dict[str, Any]:
        content_type = ""
        for key, value in dict(headers).items():
            if str(key).lower() == "content-type":
                content_type = str(value).lower()
                break
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            raise MCPDiscoveryError("BAD_JSON", "MCP server returned invalid UTF-8.") from None
        if "text/event-stream" in content_type:
            data_lines = [line[5:].lstrip() for line in text.splitlines() if line.startswith("data:")]
            if not data_lines:
                raise MCPDiscoveryError("BAD_SSE", "MCP server returned an empty event stream.")
            text = "\n".join(data_lines)
        try:
            envelope = json.loads(text)
        except json.JSONDecodeError:
            raise MCPDiscoveryError("BAD_JSON", "MCP server returned invalid JSON.") from None
        if not isinstance(envelope, dict):
            raise MCPDiscoveryError("BAD_ENVELOPE", "MCP server returned an invalid JSON-RPC envelope.")
        return envelope

    def _resolve_token(self, config: ConnectorConfig) -> str | None:
        if not config.credential_ref or self.credential_resolver is None:
            return None
        token = self.credential_resolver(config.connector_id, config.credential_ref)
        return token.strip() if token else None

    @staticmethod
    def _normalize_tool(connector_id: str, raw: dict[str, Any]) -> NormalizedTool:
        name = raw.get("name")
        if not isinstance(name, str) or not _TOOL_NAME.fullmatch(name):
            raise ValueError("invalid MCP tool name")
        description = raw.get("description", "")
        if not isinstance(description, str):
            description = ""
        input_schema = raw.get("inputSchema")
        if not isinstance(input_schema, dict) or input_schema.get("type") != "object":
            raise ValueError("MCP inputSchema must be an object schema")
        encoded = json.dumps(input_schema, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > 131_072:
            raise ValueError("MCP inputSchema exceeds size limit")
        validate_x_mcp_headers(input_schema)
        output_schema = raw.get("outputSchema")
        if output_schema is not None and not isinstance(output_schema, dict):
            raise ValueError("MCP outputSchema must be an object when present")
        annotations = raw.get("annotations")
        if not isinstance(annotations, dict):
            annotations = {}
        return NormalizedTool(
            connector_id=connector_id,
            name=name,
            description=description[:4_000],
            input_schema=input_schema,
            output_schema=output_schema,
            annotations=annotations,
            risk=classify_mcp_tool(name, annotations),
        )
