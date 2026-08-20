"""Fail-closed contract for exposing the CK-NEXUS clean-room MCP server remotely.

This module does not open a listener or mint credentials. It validates the public resource/issuer
identity and builds an OAuth-protected MCP resource server only when a caller supplies a real
TokenVerifier. Remote access tokens are additionally bound to the exact CK-NEXUS source/registry
attestation before the MCP SDK is allowed to treat them as authenticated.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from creator_app.device_bridge.mcp_server_v2 import build_server

_REQUIRED_SCOPE = "cknexus:read"
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_MAX_TOKEN_TTL_SECONDS = 15 * 60
_CLOCK_SKEW_SECONDS = 60
_ATTESTATION_CLAIM = "cknexus_attestation"


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

    def validate(self) -> RemoteBridgeConfig:
        _validate_https_url(self.resource_server_url, required_path="/mcp", require_public=True)
        _validate_https_url(self.issuer_url, require_public=True)
        if self.required_scope != _REQUIRED_SCOPE:
            raise RemoteContractError("remote_scope_must_be_read_only")
        if self.local_bind_host not in _LOOPBACK_HOSTS:
            raise RemoteContractError("remote_mcp_must_bind_loopback")
        if not 1024 <= self.local_bind_port <= 65535:
            raise RemoteContractError("remote_bind_port_invalid")
        return self


@dataclass(frozen=True)
class RemoteAttestationIdentity:
    """Exact local source/runtime identity a remote token must be minted for."""

    source_commit: str
    source_tree: str
    registry_sha256: str
    descriptor_sha256: str

    def validate(self) -> RemoteAttestationIdentity:
        _require_hex(self.source_commit, length=40, reason="source_commit_invalid")
        _require_hex(self.source_tree, length=40, reason="source_tree_invalid")
        _require_hex(self.registry_sha256, length=64, reason="registry_sha256_invalid")
        _require_hex(self.descriptor_sha256, length=64, reason="descriptor_sha256_invalid")
        return self

    def as_claim(self) -> dict[str, str]:
        self.validate()
        return asdict(self)


def _require_hex(value: str, *, length: int, reason: str) -> None:
    normalized = value.lower()
    if len(normalized) != length or any(char not in "0123456789abcdef" for char in normalized):
        raise RemoteContractError(reason)


def _validate_https_url(
    value: str,
    *,
    required_path: str | None = None,
    require_public: bool = False,
) -> None:
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

    if require_public:
        host = parsed.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
            raise RemoteContractError("remote_url_requires_public_host")
        try:
            literal_ip = ip_address(host)
        except ValueError:
            literal_ip = None
        if literal_ip is not None and not literal_ip.is_global:
            raise RemoteContractError("remote_url_requires_public_host")


def _same_url(left: str, right: str) -> bool:
    return left.rstrip("/") == right.rstrip("/")


class AttestedTokenVerifier(TokenVerifier):
    """Wrap a real verifier and fail closed unless the token targets this exact attested bridge."""

    def __init__(
        self,
        *,
        delegate: TokenVerifier,
        config: RemoteBridgeConfig,
        identity: RemoteAttestationIdentity,
        max_ttl_seconds: int = _MAX_TOKEN_TTL_SECONDS,
    ) -> None:
        if delegate is None:
            raise RemoteContractError("token_verifier_required")
        if not 60 <= max_ttl_seconds <= _MAX_TOKEN_TTL_SECONDS:
            raise RemoteContractError("token_ttl_policy_invalid")
        self._delegate = delegate
        self._config = config.validate()
        self._identity = identity.validate()
        self._max_ttl_seconds = max_ttl_seconds

    async def verify_token(self, token: str) -> AccessToken | None:
        access = await self._delegate.verify_token(token)
        if access is None:
            return None

        now = int(time.time())
        if not access.client_id or self._config.required_scope not in access.scopes:
            return None
        if access.resource is None or not _same_url(
            access.resource,
            self._config.resource_server_url,
        ):
            return None
        if access.expires_at is None or access.expires_at <= now:
            return None

        claims: dict[str, Any] = access.claims or {}
        issuer = claims.get("iss")
        issued_at = claims.get("iat")
        attestation = claims.get(_ATTESTATION_CLAIM)
        if not isinstance(issuer, str) or not _same_url(issuer, self._config.issuer_url):
            return None
        if not isinstance(issued_at, int):
            return None
        if issued_at > now + _CLOCK_SKEW_SECONDS:
            return None
        if access.expires_at - issued_at > self._max_ttl_seconds:
            return None
        if attestation != self._identity.as_claim():
            return None
        return access


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
    identity: RemoteAttestationIdentity,
    token_verifier: TokenVerifier,
) -> FastMCP:
    """Build six read-only tools behind an exact-attestation-bound bearer verifier."""
    verified = AttestedTokenVerifier(
        delegate=token_verifier,
        config=config,
        identity=identity,
    )
    return build_server(
        auth=build_remote_auth(config),
        token_verifier=verified,
        transport_label="streamable-http",
    )
