"""Fail-closed contract for exposing the CK-NEXUS clean-room MCP server remotely.

This module does not open a listener or mint credentials. It validates the public resource/issuer
identity and builds an OAuth-protected MCP resource server only when a caller supplies a real
TokenVerifier. The intended deployment shape is loopback MCP -> authenticated secure tunnel/proxy ->
public HTTPS endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl

from mcp.server.auth.provider import TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from creator_app.device_bridge.mcp_server_v2 import build_server

_REQUIRED_SCOPE = "cknexus:read"
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class RemoteContractError(ValueError):
    """Raised when a remote MCP configuration violates CK-NEXUS policy."""


@dataclass(frozen=True)
class RemoteBridgeConfig:
    """Validated metadata for one read-only remote MCP resource server."""

    resource_server_url: str
    issuer_url: str
    required_scope: str = _REQUIRED_SCOPE
    local_bind_host: str = "127.0.0.1"
    local_bind_port: int = 8767

    def validate(self) -> "RemoteBridgeConfig":
        _validate_https_url(self.resource_server_url, required_path="/mcp")
        _validate_https_url(self.issuer_url)
        if self.required_scope != _REQUIRED_SCOPE:
            raise RemoteContractError("remote_scope_must_be_read_only")
        if self.local_bind_host not in _LOOPBACK_HOSTS:
            raise RemoteContractError("remote_mcp_must_bind_loopback")
        if not 1024 <= self.local_bind_port <= 65535:
            raise RemoteContractError("remote_bind_port_invalid")
        return self


def _validate_https_url(value: str, *, required_path: str | None = None) -> None:
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise RemoteContractError("remote_url_invalid") from exc

    if parsed.scheme != "https" or not parsed.hostname:
        raise RemoteContractError("remote_url_requires_https")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RemoteContractError("remote_url_contains_forbidden_components")
    if required_path is not None and parsed.path.rstrip("/") != required_path:
        raise RemoteContractError("remote_resource_path_must_be_mcp")


def build_remote_auth(config: RemoteBridgeConfig) -> AuthSettings:
    """Build RFC 9728/OAuth resource metadata settings from validated configuration."""
    validated = config.validate()
    return AuthSettings(
        issuer_url=AnyHttpUrl(validated.issuer_url),
        resource_server_url=AnyHttpUrl(validated.resource_server_url),
        required_scopes=[validated.required_scope],
    )


def build_remote_server(
    *,
    config: RemoteBridgeConfig,
    token_verifier: TokenVerifier,
) -> FastMCP:
    """Build the same six-tool registry as local MCP, protected by bearer-token verification."""
    if token_verifier is None:
        raise RemoteContractError("token_verifier_required")
    return build_server(
        auth=build_remote_auth(config),
        token_verifier=token_verifier,
        transport_label="streamable-http",
    )
