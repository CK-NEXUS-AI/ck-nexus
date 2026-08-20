from __future__ import annotations

import time

import pytest
from mcp.server.auth.provider import AccessToken, TokenVerifier

from creator_app.device_bridge.mcp_server_v2 import TOOL_NAMES
from creator_app.device_bridge.remote_contract import (
    AttestedTokenVerifier,
    RemoteAttestationIdentity,
    RemoteBridgeConfig,
    RemoteContractError,
    build_remote_auth,
    build_remote_server,
)


class StaticVerifier(TokenVerifier):
    def __init__(self, access: AccessToken | None) -> None:
        self.access = access

    async def verify_token(self, token: str) -> AccessToken | None:
        return self.access


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


def _valid_access() -> AccessToken:
    now = int(time.time())
    return AccessToken(
        token="unit-test-token",
        client_id="gpt-client",
        scopes=["cknexus:read"],
        expires_at=now + 300,
        resource="https://bridge.example.test/mcp",
        subject="unit-test-user",
        claims={
            "iss": "https://auth.example.test",
            "iat": now,
            "cknexus_attestation": _identity().as_claim(),
        },
    )


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


def test_remote_contract_requires_public_host() -> None:
    with pytest.raises(RemoteContractError, match="remote_url_requires_public_host"):
        RemoteBridgeConfig(
            resource_server_url="https://127.0.0.1/mcp",
            issuer_url="https://auth.example.test",
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


def test_attestation_identity_rejects_malformed_digests() -> None:
    with pytest.raises(RemoteContractError, match="source_commit_invalid"):
        RemoteAttestationIdentity(
            source_commit="not-a-sha",
            source_tree="b" * 40,
            registry_sha256="c" * 64,
            descriptor_sha256="d" * 64,
        ).validate()


@pytest.mark.asyncio
async def test_attested_verifier_accepts_exact_short_lived_token() -> None:
    access = _valid_access()
    verifier = AttestedTokenVerifier(
        delegate=StaticVerifier(access),
        config=_config(),
        identity=_identity(),
    )

    assert await verifier.verify_token("opaque") is access


@pytest.mark.asyncio
async def test_attested_verifier_denies_wrong_resource_or_attestation() -> None:
    wrong_resource = _valid_access().model_copy(
        update={"resource": "https://other.example.test/mcp"}
    )
    verifier = AttestedTokenVerifier(
        delegate=StaticVerifier(wrong_resource),
        config=_config(),
        identity=_identity(),
    )
    assert await verifier.verify_token("opaque") is None

    wrong_claims = dict(_valid_access().claims or {})
    wrong_claims["cknexus_attestation"] = {
        **_identity().as_claim(),
        "registry_sha256": "e" * 64,
    }
    wrong_attestation = _valid_access().model_copy(update={"claims": wrong_claims})
    verifier = AttestedTokenVerifier(
        delegate=StaticVerifier(wrong_attestation),
        config=_config(),
        identity=_identity(),
    )
    assert await verifier.verify_token("opaque") is None


@pytest.mark.asyncio
async def test_attested_verifier_denies_expired_or_long_lived_token() -> None:
    now = int(time.time())
    expired = _valid_access().model_copy(update={"expires_at": now - 1})
    verifier = AttestedTokenVerifier(
        delegate=StaticVerifier(expired),
        config=_config(),
        identity=_identity(),
    )
    assert await verifier.verify_token("opaque") is None

    long_lived = _valid_access().model_copy(update={"expires_at": now + 3600})
    verifier = AttestedTokenVerifier(
        delegate=StaticVerifier(long_lived),
        config=_config(),
        identity=_identity(),
    )
    assert await verifier.verify_token("opaque") is None


def test_auth_settings_and_remote_server_are_fail_closed() -> None:
    config = _config()
    auth = build_remote_auth(config)

    assert auth.required_scopes == ["cknexus:read"]
    assert str(auth.resource_server_url).rstrip("/") == "https://bridge.example.test/mcp"

    server = build_remote_server(
        config=config,
        identity=_identity(),
        token_verifier=StaticVerifier(None),
    )
    assert server.settings.auth is not None
    assert server.settings.auth.required_scopes == ["cknexus:read"]
    assert len(TOOL_NAMES) == 6


def test_missing_token_verifier_is_denied() -> None:
    with pytest.raises(RemoteContractError, match="token_verifier_required"):
        build_remote_server(
            config=_config(),
            identity=_identity(),
            token_verifier=None,  # type: ignore[arg-type]
        )
