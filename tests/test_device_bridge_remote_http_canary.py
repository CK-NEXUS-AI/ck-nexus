from __future__ import annotations

import time

import httpx
import pytest
from mcp.server.auth.provider import AccessToken, TokenVerifier

from creator_app.device_bridge.mcp_server_v2 import TOOL_NAMES
from creator_app.device_bridge.remote_contract import (
    RemoteAttestationIdentity,
    RemoteBridgeConfig,
    build_remote_server,
)


class MappingVerifier(TokenVerifier):
    def __init__(self, values: dict[str, AccessToken]) -> None:
        self.values = values

    async def verify_token(self, token: str) -> AccessToken | None:
        return self.values.get(token)


def _config() -> RemoteBridgeConfig:
    return RemoteBridgeConfig(
        resource_server_url="https://bridge.example.test/mcp",
        issuer_url="https://auth.example.test",
    )


def _identity() -> RemoteAttestationIdentity:
    return RemoteAttestationIdentity(
        source_commit="a" * 40,
        source_tree="b" * 40,
        registry_sha256="c" * 64,
        descriptor_sha256="d" * 64,
    )


def _access(*, scopes: list[str] | None = None) -> AccessToken:
    now = int(time.time())
    return AccessToken(
        token="fixture-token",
        client_id="gpt-canary",
        scopes=["cknexus:read"] if scopes is None else scopes,
        expires_at=now + 300,
        resource="https://bridge.example.test/mcp",
        subject="canary-user",
        claims={
            "iss": "https://auth.example.test",
            "iat": now,
            "cknexus_attestation": _identity().as_claim(),
        },
    )


def _initialize() -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "ck-nexus-canary", "version": "1"},
        },
    }


def _headers(token: str | None = None) -> dict[str, str]:
    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
    }
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    return headers


@pytest.mark.asyncio
async def test_remote_http_auth_status_semantics_and_valid_initialize() -> None:
    server = build_remote_server(
        config=_config(),
        identity=_identity(),
        token_verifier=MappingVerifier(
            {
                "valid": _access(),
                "no-scope": _access(scopes=[]),
            }
        ),
    )
    app = server.streamable_http_app()
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://localhost:8767",
        ) as client:
            missing = await client.post("/mcp", json=_initialize(), headers=_headers())
            invalid = await client.post(
                "/mcp",
                json=_initialize(),
                headers=_headers("invalid"),
            )
            insufficient = await client.post(
                "/mcp",
                json=_initialize(),
                headers=_headers("no-scope"),
            )
            valid = await client.post(
                "/mcp",
                json=_initialize(),
                headers=_headers("valid"),
            )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert insufficient.status_code == 403
    assert valid.status_code == 200
    assert valid.json()["result"]["serverInfo"]["name"]


@pytest.mark.asyncio
async def test_remote_http_rejects_bad_host_origin_and_oversized_body() -> None:
    server = build_remote_server(
        config=_config(),
        identity=_identity(),
        token_verifier=MappingVerifier({"valid": _access()}),
    )
    app = server.streamable_http_app()
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://localhost:8767",
        ) as client:
            bad_host_headers = _headers("valid")
            bad_host_headers["host"] = "evil.example"
            bad_host = await client.post(
                "/mcp",
                json=_initialize(),
                headers=bad_host_headers,
            )

            bad_origin_headers = _headers("valid")
            bad_origin_headers["origin"] = "https://evil.example"
            bad_origin = await client.post(
                "/mcp",
                json=_initialize(),
                headers=bad_origin_headers,
            )

            oversized = await client.post(
                "/mcp",
                content=b"x" * (64 * 1024 + 1),
                headers=_headers("valid"),
            )

    assert bad_host.status_code == 421
    assert bad_origin.status_code == 403
    assert oversized.status_code == 413


@pytest.mark.asyncio
async def test_remote_registry_remains_exactly_six_read_only_tools() -> None:
    server = build_remote_server(
        config=_config(),
        identity=_identity(),
        token_verifier=MappingVerifier({"valid": _access()}),
    )
    tools = await server.list_tools()

    assert {tool.name for tool in tools} == set(TOOL_NAMES)
    assert len(tools) == 6
    for tool in tools:
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is False
