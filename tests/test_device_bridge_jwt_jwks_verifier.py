from __future__ import annotations

import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from creator_app.device_bridge.jwt_jwks_verifier import JwtJwksTokenVerifier, JwtJwksVerifierConfig


@pytest.fixture
def key_material():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_numbers()
    import base64
    enc = lambda n: base64.urlsafe_b64encode(n.to_bytes((n.bit_length()+7)//8, 'big')).rstrip(b'=').decode()
    jwk = {"kty": "RSA", "kid": "kid-1", "alg": "RS256", "use": "sig", "n": enc(public.n), "e": enc(public.e)}
    return key, jwk


def config():
    return JwtJwksVerifierConfig(
        issuer_url="https://issuer.example.test",
        jwks_url="https://issuer.example.test/.well-known/jwks.json",
        resource_server_url="https://bridge.example.test/mcp",
        allowed_algorithms=("RS256",),
    )


def signed_token(key, **claims):
    now = int(time.time())
    payload = {
        "iss": "https://issuer.example.test",
        "sub": "user-1",
        "client_id": "client-1",
        "aud": "https://bridge.example.test/mcp",
        "iat": now,
        "exp": now + 300,
        "scope": "cknexus:read",
        "cknexus_attestation": {"source_commit": "a" * 40, "source_tree": "b" * 40, "registry_sha256": "c" * 64, "descriptor_sha256": "d" * 64},
        **claims,
    }
    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": "kid-1"})


def verifier(key_jwk, calls=None):
    def handler(request: httpx.Request):
        if calls is not None:
            calls.append(str(request.url))
        return httpx.Response(200, json={"keys": [key_jwk]})
    return JwtJwksTokenVerifier(config(), transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_valid_signed_token_is_converted_to_access_token(key_material):
    key, jwk = key_material
    access = await verifier(jwk).verify_token(signed_token(key))
    assert access is not None
    assert access.client_id == "client-1"
    assert access.scopes == ["cknexus:read"]
    assert access.resource == "https://bridge.example.test/mcp"
    assert access.claims["iss"] == "https://issuer.example.test"


def test_config_rejects_http_and_empty_or_symmetric_algorithms():
    with pytest.raises(ValueError):
        JwtJwksVerifierConfig("http://issuer.example.test", "https://issuer.example.test/jwks", "https://bridge.example.test/mcp", ("RS256",))
    with pytest.raises(ValueError):
        JwtJwksVerifierConfig("https://issuer.example.test", "https://issuer.example.test/jwks", "https://bridge.example.test/mcp", ())
    with pytest.raises(ValueError):
        JwtJwksVerifierConfig("https://issuer.example.test", "https://issuer.example.test/jwks", "https://bridge.example.test/mcp", ("HS256",))


@pytest.mark.asyncio
@pytest.mark.parametrize("mutate", [
    lambda c: c.__setitem__("iss", "https://other.example.test"),
    lambda c: c.__setitem__("aud", "https://other.example.test/mcp"),
    lambda c: c.__setitem__("exp", int(time.time()) - 10),
    lambda c: c.pop("exp"),
    lambda c: c.__setitem__("iat", int(time.time()) + 120),
])
async def test_invalid_claims_fail_closed(key_material, mutate):
    key, jwk = key_material
    # Test helper intentionally mutates a freshly constructed payload through JWT decode-free signing.
    now = int(time.time())
    claims = {"iss": "https://issuer.example.test", "sub": "user-1", "client_id": "client-1", "aud": "https://bridge.example.test/mcp", "iat": now, "exp": now + 300, "scope": "cknexus:read"}
    mutate(claims)
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "kid-1"})
    assert await verifier(jwk).verify_token(token) is None


@pytest.mark.asyncio
async def test_bad_signature_unknown_kid_and_unsupported_algorithm_fail(key_material):
    key, jwk = key_material
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    bad_signature = signed_token(other)
    assert await verifier(jwk).verify_token(bad_signature) is None
    unknown_kid = jwt.encode({"iss":"https://issuer.example.test","aud":"https://bridge.example.test/mcp","iat":int(time.time()),"exp":int(time.time())+300}, key, algorithm="RS256", headers={"kid":"unknown"})
    assert await verifier(jwk).verify_token(unknown_kid) is None


@pytest.mark.asyncio
async def test_unknown_kid_refreshes_once(key_material):
    key, jwk = key_material
    calls = []
    def handler(request):
        calls.append(str(request.url))
        if len(calls) == 1:
            return httpx.Response(200, json={"keys": [{**jwk, "kid": "old"}]})
        return httpx.Response(200, json={"keys": [jwk]})
    v = JwtJwksTokenVerifier(config(), transport=httpx.MockTransport(handler))
    assert await v.verify_token(signed_token(key)) is not None
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_cache_avoids_repeated_jwks_fetch(key_material):
    key, jwk = key_material
    calls = []
    v = verifier(jwk, calls)
    token = signed_token(key)
    assert await v.verify_token(token)
    assert await v.verify_token(token)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_long_lived_token_is_rejected(key_material):
    key, jwk = key_material
    now = int(time.time())
    token = signed_token(key, iat=now, exp=now + 901)
    assert await verifier(jwk).verify_token(token) is None


@pytest.mark.asyncio
async def test_jwks_failure_fails_closed(key_material):
    key, _ = key_material
    def handler(request):
        return httpx.Response(503, text="upstream unavailable")
    v = JwtJwksTokenVerifier(config(), transport=httpx.MockTransport(handler))
    assert await v.verify_token(signed_token(key)) is None


@pytest.mark.asyncio
async def test_credential_material_is_not_in_exception_text(key_material):
    key, _ = key_material
    token = signed_token(key)
    def handler(request):
        raise RuntimeError("upstream failure")
    v = JwtJwksTokenVerifier(config(), transport=httpx.MockTransport(handler))
    assert await v.verify_token(token) is None
