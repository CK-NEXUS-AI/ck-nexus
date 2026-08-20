from __future__ import annotations

import pytest

from mcp.server.auth.provider import AccessToken, TokenVerifier

from creator_app.device_bridge.mcp_server_v2 import TOOL_NAMES
from creator_app.device_bridge.remote_contract import (
    RemoteBridgeConfig,
    RemoteContractError,
    build_remote_auth,
    build_remote_server,
)


class DenyAllVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        return None


def test_remote_contract_requires_https_resource_and_issuer() -> None:
    with pytest.raises(RemoteContractError, match="remote_url_requires_https"):
        RemoteBridgeConfig(
            resource_server_url="http://bridge.example.test/mcp",
            issuer_url="https://auth.example.test",
        ).validate()

    with pytest.raises(RemoteContractError, match="remote_url_requires_https"):
        RemoteBridgeConfig(
            resource_server_url="https://bridge.example.test/mcp",
            issuer_url="http://auth.example.test",
        ).validate()


def test_remote_contract_requires_exact_mcp_path_and_no_url_secrets() -> None:
    with pytest.raises(RemoteContractError, match="remote_resource_path_must_be_mcp"):
        RemoteBridgeConfig(
            resource_server_url="https://bridge.example.test/api",
            issuer_url="https://auth.example.test",
        ).validate()

    with pytest.raises(RemoteContractError, match="remote_url_contains_forbidden_components"):
        RemoteBridgeConfig(
            resource_server_url="https://user:password@bridge.example.test/mcp",
            issuer_url="https://auth.example.test",
        ).validate()


def test_remote_contract_is_read_only_and_loopback_bound() -> None:
    with pytest.raises(RemoteContractError, match="remote_scope_must_be_read_only"):
        RemoteBridgeConfig(
            resource_server_url="https://bridge.example.test/mcp",
            issuer_url="https://auth.example.test",
            required_scope="cknexus:write",
        ).validate()

    with pytest.raises(RemoteContractError, match="remote_mcp_must_bind_loopback"):
        RemoteBridgeConfig(
            resource_server_url="https://bridge.example.test/mcp",
            issuer_url="https://auth.example.test",
            local_bind_host="0.0.0.0",
        ).validate()


def test_auth_settings_and_remote_server_are_fail_closed() -> None:
    config = RemoteBridgeConfig(
        resource_server_url="https://bridge.example.test/mcp",
        issuer_url="https://auth.example.test",
    )
    auth = build_remote_auth(config)

    assert auth.required_scopes == ["cknexus:read"]
    assert str(auth.resource_server_url).rstrip("/") == "https://bridge.example.test/mcp"

    server = build_remote_server(config=config, token_verifier=DenyAllVerifier())
    assert server.settings.auth is not None
    assert server.settings.auth.required_scopes == ["cknexus:read"]
    assert len(TOOL_NAMES) == 6


def test_missing_token_verifier_is_denied() -> None:
    config = RemoteBridgeConfig(
        resource_server_url="https://bridge.example.test/mcp",
        issuer_url="https://auth.example.test",
    )

    with pytest.raises(RemoteContractError, match="token_verifier_required"):
        build_remote_server(config=config, token_verifier=None)  # type: ignore[arg-type]
