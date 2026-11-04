from __future__ import annotations

import pytest

from creator_app.device_bridge.mcp_2026_07_28 import (
    MCP2026ContractError,
    MCP2026Request,
    MCP_PROTOCOL_VERSION,
    validate_transport,
)


def test_mcp_2026_request_builds_stateless_gateway_headers() -> None:
    request = MCP2026Request(
        method="tools/call",
        name="workspace_sha256",
        capabilities=("tools.read", "tasks.observe"),
    )

    headers = request.gateway_headers()

    assert headers["MCP-Protocol-Version"] == MCP_PROTOCOL_VERSION
    assert headers["Mcp-Method"] == "tools/call"
    assert headers["Mcp-Name"] == "workspace_sha256"
    assert all("session" not in key.lower() for key in headers)
    request.validate_gateway_headers(headers)


def test_mcp_2026_rejects_legacy_initialize_handshake() -> None:
    with pytest.raises(MCP2026ContractError, match="legacy_initialize_handshake_denied"):
        MCP2026Request(method="initialize").validate()

    with pytest.raises(MCP2026ContractError, match="legacy_initialize_handshake_denied"):
        MCP2026Request(method="notifications/initialized").validate()


def test_mcp_2026_rejects_protocol_session_headers() -> None:
    request = MCP2026Request(method="tools/list")
    headers = request.gateway_headers()
    headers["Mcp-Session-Id"] = "legacy-session"

    with pytest.raises(MCP2026ContractError, match="protocol_session_header_denied"):
        request.validate_gateway_headers(headers)


def test_mcp_2026_rejects_gateway_routing_mismatch() -> None:
    request = MCP2026Request(method="tools/call", name="workspace_read_text")

    with pytest.raises(MCP2026ContractError, match="mcp_method_header_mismatch"):
        request.validate_gateway_headers(
            {
                "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
                "Mcp-Method": "tools/list",
                "Mcp-Name": "workspace_read_text",
            }
        )


def test_mcp_2026_list_cache_key_is_deterministic_and_task_scoped_lists_are_not_cached() -> None:
    request = MCP2026Request(method="tools/list", capabilities=("tools.read",))
    first = request.cache_key({"cursor": "A"})
    second = request.cache_key({"cursor": "A"})

    assert first == second
    assert first is not None
    assert first.startswith("mcp-list-")

    task_request = MCP2026Request(
        method="tools/list",
        capabilities=("tools.read",),
        task_id="TASK-1",
    )
    assert task_request.cache_key({"cursor": "A"}) is None


def test_mcp_2026_evidence_contains_digest_not_raw_params() -> None:
    request = MCP2026Request(method="tools/call", name="workspace_read_text")
    evidence = request.evidence_projection({"path": "private-plan.txt"})

    assert evidence["stateless"] is True
    assert evidence["legacy_initialize_allowed"] is False
    assert len(evidence["params_sha256"]) == 64
    assert "private-plan.txt" not in str(evidence)


def test_mcp_2026_transport_rejects_legacy_sse() -> None:
    assert validate_transport("streamable-http") == "streamable-http"
    assert validate_transport("stdio") == "stdio"
    with pytest.raises(MCP2026ContractError, match="legacy_or_unsupported_transport"):
        validate_transport("sse")
