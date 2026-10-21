from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx
import jwt
from mcp.server.auth.provider import AccessToken, TokenVerifier

_MAX_TOKEN_TTL_SECONDS = 15 * 60
_CLOCK_SKEW_SECONDS = 60
_MAX_JWKS_BYTES = 1024 * 1024
_ALLOWED_ASYMMETRIC_ALGORITHMS = frozenset(
    {"RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512"}
)


@dataclass(frozen=True)
class JwtJwksVerifierConfig:
    issuer_url: str
    jwks_url: str
    resource_server_url: str
    allowed_algorithms: tuple[str, ...]
    http_timeout_seconds: float = 5.0
    jwks_cache_seconds: int = 300
    max_jwks_bytes: int = _MAX_JWKS_BYTES

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> JwtJwksVerifierConfig:
        for name, value in (("issuer_url", self.issuer_url), ("jwks_url", self.jwks_url)):
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.query or parsed.fragment:
                raise ValueError(f"{name}_must_be_https_without_query_or_fragment")
        if not self.resource_server_url or "#" in self.resource_server_url:
            raise ValueError("resource_server_url_invalid")
        if not self.allowed_algorithms or any(
            algorithm not in _ALLOWED_ASYMMETRIC_ALGORITHMS for algorithm in self.allowed_algorithms
        ):
            raise ValueError("allowed_algorithms_must_be_explicit_asymmetric_algorithms")
        if not 0.5 <= self.http_timeout_seconds <= 30:
            raise ValueError("http_timeout_seconds_out_of_bounds")
        if not 30 <= self.jwks_cache_seconds <= 3600:
            raise ValueError("jwks_cache_seconds_out_of_bounds")
        if not 1024 <= self.max_jwks_bytes <= _MAX_JWKS_BYTES:
            raise ValueError("max_jwks_bytes_out_of_bounds")
        return self


class JwtJwksTokenVerifier(TokenVerifier):
    """Fail-closed JWT/JWKS verifier for a single OAuth resource server."""

    def __init__(
        self,
        config: JwtJwksVerifierConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: callable = time.time,
    ) -> None:
        self.config = config.validate()
        self._transport = transport
        self._clock = clock
        self._jwks: dict[str, dict[str, Any]] = {}
        self._jwks_expires_at = 0.0
        self._lock = asyncio.Lock()

    async def verify_token(self, token: str) -> AccessToken | None:
        if not isinstance(token, str) or not token or len(token) > 64 * 1024:
            return None
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            kid = header.get("kid")
            if algorithm not in self.config.allowed_algorithms or not isinstance(kid, str) or not kid:
                return None
            jwk = await self._get_key(kid, refresh_if_missing=True)
            if jwk is None:
                return None
            if jwk.get("alg") not in (None, algorithm) or jwk.get("use") not in (None, "sig"):
                return None
            key = jwt.PyJWK.from_dict(jwk, algorithm=algorithm).key
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                issuer=self.config.issuer_url,
                audience=self.config.resource_server_url,
                options={"require": ["iss", "aud", "exp", "iat"]},
            )
            now = int(self._clock())
            issued_at = claims.get("iat")
            expires_at = claims.get("exp")
            if isinstance(issued_at, bool) or not isinstance(issued_at, int):
                return None
            if isinstance(expires_at, bool) or not isinstance(expires_at, int):
                return None
            if issued_at > now + _CLOCK_SKEW_SECONDS or expires_at <= now:
                return None
            if expires_at - issued_at > _MAX_TOKEN_TTL_SECONDS:
                return None
            resource_claim = claims.get("resource")
            if resource_claim is not None and resource_claim != self.config.resource_server_url:
                return None
            client_id = claims.get("client_id") or claims.get("azp") or claims.get("sub")
            if not isinstance(client_id, str) or not client_id:
                return None
            scopes = _scopes_from_claim(claims.get("scope"))
            return AccessToken(
                token=token,
                client_id=client_id,
                scopes=scopes,
                expires_at=expires_at,
                resource=self.config.resource_server_url,
                subject=claims.get("sub") if isinstance(claims.get("sub"), str) else None,
                claims=claims,
            )
        except Exception:
            return None

    async def _get_key(self, kid: str, *, refresh_if_missing: bool) -> dict[str, Any] | None:
        now = self._clock()
        if now >= self._jwks_expires_at:
            await self._refresh_jwks()
        key = self._jwks.get(kid)
        if key is not None or not refresh_if_missing:
            return key
        if await self._refresh_jwks(force=True):
            return self._jwks.get(kid)
        return None

    async def _refresh_jwks(self, *, force: bool = False) -> bool:
        async with self._lock:
            now = self._clock()
            if not force and now < self._jwks_expires_at and self._jwks:
                return True
            try:
                async with httpx.AsyncClient(
                    transport=self._transport,
                    timeout=self.config.http_timeout_seconds,
                ) as client:
                    response = await client.get(self.config.jwks_url)
                    if response.status_code != 200:
                        return False
                    content_length = response.headers.get("content-length")
                    if content_length is not None and int(content_length) > self.config.max_jwks_bytes:
                        return False
                    body = await response.aread()
                    if len(body) > self.config.max_jwks_bytes:
                        return False
                    document = json.loads(body)
                    keys = document.get("keys")
                    if not isinstance(keys, list):
                        return False
                    parsed: dict[str, dict[str, Any]] = {}
                    for item in keys:
                        if isinstance(item, dict) and isinstance(item.get("kid"), str):
                            parsed[item["kid"]] = item
                    if not parsed:
                        return False
                    self._jwks = parsed
                    self._jwks_expires_at = now + self.config.jwks_cache_seconds
                    return True
            except Exception:
                return False


def _scopes_from_claim(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item for item in value.split() if item]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return []
