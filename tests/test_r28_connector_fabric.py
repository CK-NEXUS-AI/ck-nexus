from __future__ import annotations

import json

import pytest

from creator_app.connector_fabric.evidence import ConnectorEvidenceLedger
from creator_app.connector_fabric.fabric import ConnectorFabric, ToolAuthorizationDecision
from creator_app.connector_fabric.mcp import MCP_PROTOCOL_VERSION, MCPClient
from creator_app.connector_fabric.models import (
    ConnectorConfig,
    ConnectorProtocol,
    ConnectorState,
    RiskClass,
)
from creator_app.connector_fabric.openapi import OpenAPIClient
from creator_app.connector_fabric.registry import ConnectorRegistry
from creator_app.connector_fabric.security import (
    EndpointPolicy,
    EndpointSecurityError,
    validate_endpoint,
)
from creator_app.connector_fabric.transport import TransportResponse


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, method, url, *, headers, body, timeout):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)


def rpc_result(request_id: int, result: dict) -> TransportResponse:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "result": {"resultType": "complete", **result}}
    ).encode()
    return TransportResponse(200, {"Content-Type": "application/json"}, body)


def rpc_error(request_id: int, code: int) -> TransportResponse:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": "x"}}
    ).encode()
    return TransportResponse(200, {"Content-Type": "application/json"}, body)


def test_endpoint_policy_blocks_private_and_query_credentials():
    with pytest.raises(EndpointSecurityError):
        validate_endpoint("http://127.0.0.1/mcp", resolver=lambda host: ["127.0.0.1"])
    with pytest.raises(EndpointSecurityError):
        validate_endpoint(
            "https://example.com/mcp?token=secret", resolver=lambda host: ["93.184.216.34"]
        )
    assert validate_endpoint(
        "http://127.0.0.1/mcp",
        policy=EndpointPolicy(allow_private_network=True),
        resolver=lambda host: ["127.0.0.1"],
    ) == ("127.0.0.1",)


def test_mcp_2026_discovery_paginates_and_rejects_unsafe_tool(monkeypatch):
    monkeypatch.setattr(
        "creator_app.connector_fabric.mcp.validate_endpoint", lambda *args, **kwargs: ("127.0.0.1",)
    )
    transport = FakeTransport(
        [
            rpc_result(
                1, {"supportedVersions": [MCP_PROTOCOL_VERSION], "capabilities": {"tools": {}}}
            ),
            rpc_result(
                2,
                {
                    "tools": [
                        {
                            "name": "get.status",
                            "description": "read status",
                            "inputSchema": {"type": "object", "properties": {}},
                            "annotations": {"readOnlyHint": True},
                        }
                    ],
                    "nextCursor": "p2",
                    "ttlMs": 5000,
                    "cacheScope": "private",
                },
            ),
            rpc_result(
                3,
                {
                    "tools": [
                        {
                            "name": "delete_all",
                            "inputSchema": {"type": "object", "properties": {}},
                            "annotations": {"destructiveHint": True},
                        },
                        {
                            "name": "unsafe",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "string", "x-mcp-header": "Authorization"}
                                },
                            },
                        },
                    ]
                },
            ),
            rpc_error(4, -32601),
            rpc_error(5, -32601),
        ]
    )
    client = MCPClient(transport=transport)
    config = ConnectorConfig(
        connector_id="demo",
        url="http://127.0.0.1/mcp",
        protocol=ConnectorProtocol.MCP,
        allow_private_network=True,
    )
    snap = client.discover(config)
    assert [tool.name for tool in snap.tools] == ["delete_all", "get.status"]
    assert snap.tools[0].risk is RiskClass.DESTRUCTIVE
    assert snap.tools[1].risk is RiskClass.READ_ONLY
    assert snap.cache_ttl_ms == 5000
    assert snap.cache_scope == "private"
    assert snap.rejected_tools[0]["name"] == "unsafe"
    assert transport.requests[0]["headers"]["Mcp-Method"] == "server/discover"
    assert "Mcp-Name" not in transport.requests[1]["headers"]
    first_list = json.loads(transport.requests[1]["body"])
    assert (
        first_list["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"]
        == MCP_PROTOCOL_VERSION
    )
    second_list = json.loads(transport.requests[2]["body"])
    assert second_list["params"]["cursor"] == "p2"


def test_connector_fabric_read_only_binding_and_fail_closed_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "creator_app.connector_fabric.mcp.validate_endpoint", lambda *args, **kwargs: ("127.0.0.1",)
    )
    transport = FakeTransport(
        [
            rpc_result(
                1, {"supportedVersions": [MCP_PROTOCOL_VERSION], "capabilities": {"tools": {}}}
            ),
            rpc_result(
                2,
                {
                    "tools": [
                        {
                            "name": "get_status",
                            "description": "read status",
                            "inputSchema": {"type": "object", "properties": {}},
                            "annotations": {"readOnlyHint": True},
                        },
                        {
                            "name": "send_message",
                            "description": "write",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"text": {"type": "string"}},
                            },
                        },
                    ]
                },
            ),
            rpc_error(3, -32601),
            rpc_error(4, -32601),
        ]
    )
    fabric = ConnectorFabric(
        registry=ConnectorRegistry(tmp_path / "registry.json"),
        evidence=ConnectorEvidenceLedger(tmp_path / "evidence.jsonl"),
        mcp_client=MCPClient(transport=transport),
    )
    fabric.register(
        ConnectorConfig(
            "demo", "http://127.0.0.1/mcp", ConnectorProtocol.MCP, allow_private_network=True
        )
    )
    record = fabric.discover("demo")
    assert record.state is ConnectorState.SCHEMA_VERIFIED
    fabric.activate("demo")
    exposed = fabric.model_tools("demo")
    assert [item["name"] for item in exposed] == ["demo.get_status"]
    with pytest.raises(PermissionError):
        fabric.invoke("demo", "get_status", {})
    with pytest.raises(PermissionError):
        fabric.invoke("demo", "send_message", {"text": "x"})


class AllowAuthorizer:
    def authorize(self, **kwargs):
        return ToolAuthorizationDecision(True, "test")


def test_connector_fabric_can_invoke_verified_mcp_tool_with_authorizer(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "creator_app.connector_fabric.mcp.validate_endpoint", lambda *args, **kwargs: ("127.0.0.1",)
    )
    transport = FakeTransport(
        [
            rpc_result(
                1, {"supportedVersions": [MCP_PROTOCOL_VERSION], "capabilities": {"tools": {}}}
            ),
            rpc_result(
                2,
                {
                    "tools": [
                        {
                            "name": "get_status",
                            "inputSchema": {"type": "object", "properties": {}},
                            "annotations": {"readOnlyHint": True},
                        }
                    ]
                },
            ),
            rpc_error(3, -32601),
            rpc_error(4, -32601),
            rpc_result(5, {"content": [{"type": "text", "text": "ok"}], "isError": False}),
        ]
    )
    fabric = ConnectorFabric(
        registry=ConnectorRegistry(tmp_path / "registry.json"),
        evidence=ConnectorEvidenceLedger(tmp_path / "evidence.jsonl"),
        mcp_client=MCPClient(transport=transport),
        authorizer=AllowAuthorizer(),
    )
    config = ConnectorConfig(
        "demo", "http://127.0.0.1/mcp", ConnectorProtocol.MCP, allow_private_network=True
    )
    fabric.register(config)
    fabric.discover("demo")
    fabric.activate("demo")
    result = fabric.invoke("demo", "get_status", {})
    assert result["content"][0]["text"] == "ok"
    call_req = transport.requests[-1]
    assert call_req["headers"]["Mcp-Method"] == "tools/call"
    assert call_req["headers"]["Mcp-Name"] == "get_status"


def test_openapi_discovery_normalizes_and_classifies_operations(monkeypatch):
    monkeypatch.setattr(
        "creator_app.connector_fabric.openapi.validate_endpoint",
        lambda *args, **kwargs: ("93.184.216.34",),
    )
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "Demo", "version": "1"},
        "paths": {
            "/users/{id}": {
                "get": {
                    "operationId": "get_user",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {"name": "Authorization", "in": "header", "schema": {"type": "string"}},
                    ],
                },
                "delete": {"operationId": "delete_user"},
            },
            "/messages": {
                "post": {
                    "operationId": "send_message",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"text": {"type": "string"}},
                                }
                            }
                        },
                    },
                }
            },
        },
    }
    transport = FakeTransport(
        [TransportResponse(200, {"Content-Type": "application/json"}, json.dumps(spec).encode())]
    )
    client = OpenAPIClient(transport=transport)
    snap = client.discover(
        ConnectorConfig("api", "https://example.com/openapi.json", ConnectorProtocol.OPENAPI)
    )
    by_name = {tool.name: tool for tool in snap.tools}
    assert by_name["get_user"].risk is RiskClass.READ_ONLY
    assert by_name["send_message"].risk is RiskClass.WRITE
    assert by_name["delete_user"].risk is RiskClass.DESTRUCTIVE
    assert "Authorization" not in by_name["get_user"].input_schema["properties"]
    assert by_name["get_user"].input_schema["required"] == ["id"]


def test_registry_reloads_only_safe_config_and_requires_rediscovery(tmp_path):
    path = tmp_path / "registry.json"
    registry = ConnectorRegistry(path)
    registry.register(
        ConnectorConfig(
            "demo",
            "https://example.com/mcp",
            ConnectorProtocol.MCP,
            credential_ref="github.installation_token",
        )
    )
    loaded = ConnectorRegistry(path)
    record = loaded.get("demo")
    assert record.config.url == "https://example.com/mcp"
    assert record.config.credential_ref == "github.installation_token"
    assert record.state is ConnectorState.REGISTERED
    text = path.read_text()
    assert "secret" not in text.lower()


def test_evidence_ledger_is_hash_chained(tmp_path):
    ledger = ConnectorEvidenceLedger(tmp_path / "evidence.jsonl")
    one = ledger.append("one", "demo", {"status": "PASS"})
    two = ledger.append("two", "demo", {"status": "PASS"})
    assert two["previousHash"] == one["entryHash"]
    assert two["entryHash"] != one["entryHash"]
