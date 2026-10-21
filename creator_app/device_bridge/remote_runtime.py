from __future__ import annotations

import os
from collections.abc import Mapping

from creator_app.device_bridge.jwt_jwks_verifier import JwtJwksTokenVerifier, JwtJwksVerifierConfig
from creator_app.device_bridge.remote_contract import (
    RemoteAttestationIdentity,
    RemoteBridgeConfig,
    build_remote_server,
)


def build_remote_server_from_environment(
    environ: Mapping[str, str] | None = None,
):
    """Build the authenticated loopback Remote MCP server from explicit deployment config."""
    values = os.environ if environ is None else environ
    resource_url = _required(values, "CKNEXUS_REMOTE_RESOURCE_URL")
    issuer_url = _required(values, "CKNEXUS_REMOTE_ISSUER_URL")
    jwks_url = _required(values, "CKNEXUS_REMOTE_JWKS_URL")
    algorithms = tuple(
        item.strip() for item in _required(values, "CKNEXUS_REMOTE_ALLOWED_ALGORITHMS").split(",") if item.strip()
    )
    bridge_config = RemoteBridgeConfig(
        resource_server_url=resource_url,
        issuer_url=issuer_url,
    ).validate()
    verifier_config = JwtJwksVerifierConfig(
        issuer_url=issuer_url,
        jwks_url=jwks_url,
        resource_server_url=resource_url,
        allowed_algorithms=algorithms,
    )
    identity = RemoteAttestationIdentity(
        source_commit=_required(values, "CKNEXUS_REMOTE_SOURCE_COMMIT"),
        source_tree=_required(values, "CKNEXUS_REMOTE_SOURCE_TREE"),
        registry_sha256=_required(values, "CKNEXUS_REMOTE_REGISTRY_SHA256"),
        descriptor_sha256=_required(values, "CKNEXUS_REMOTE_DESCRIPTOR_SHA256"),
    ).validate()
    verifier = JwtJwksTokenVerifier(verifier_config)
    return build_remote_server(
        config=bridge_config,
        identity=identity,
        token_verifier=verifier,
    )


def _required(values: Mapping[str, str], name: str) -> str:
    value = values.get(name)
    if not value:
        raise ValueError(f"{name}_required")
    return value
