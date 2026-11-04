from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass


class GatewayServiceAuthError(PermissionError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except Exception as exc:
        raise GatewayServiceAuthError("malformed service token encoding") from exc
    if _b64(decoded) != value:
        raise GatewayServiceAuthError("non-canonical service token encoding")
    return decoded
@dataclass(frozen=True, slots=True)
class GatewayServiceClaims:
    tenant_id: str
    actor_id: str
    method: str
    path: str


class GatewayServiceAuth:
    ISSUER = "ck-nexus-gateway"
    AUDIENCE = "creator-runtime"
    MAX_TTL_SECONDS = 60
    CLOCK_SKEW_SECONDS = 5

    def __init__(self, secret: str) -> None:
        encoded = secret.encode("utf-8")
        if len(encoded) < 32:
            raise ValueError("gateway service-auth secret must be at least 32 bytes")
        self._secret = encoded
    def issue(
        self,
        *,
        tenant_id: str,
        actor_id: str,
        method: str,
        path: str,
        ttl_seconds: int = 30,
        now: int | None = None,
    ) -> str:
        if ttl_seconds <= 0 or ttl_seconds > self.MAX_TTL_SECONDS:
            raise ValueError("invalid gateway service-token TTL")
        issued_at = int(time.time()) if now is None else int(now)
        payload = {
            "iss": self.ISSUER,
            "aud": self.AUDIENCE,
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "method": method.upper(),
            "path": path,
            "iat": issued_at,
            "exp": issued_at + ttl_seconds,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        body = _b64(raw)
        signature = _b64(hmac.new(self._secret, body.encode("ascii"), hashlib.sha256).digest())
        return f"{body}.{signature}"

    def verify(
        self,
        token: str,
        *,
        tenant_id: str,
        actor_id: str,
        method: str,
        path: str,
        now: int | None = None,
    ) -> GatewayServiceClaims:
        try:
            body, encoded_signature = token.split(".", 1)
        except ValueError as exc:
            raise GatewayServiceAuthError("malformed gateway service token") from exc
        expected = hmac.new(self._secret, body.encode("ascii"), hashlib.sha256).digest()
        supplied = _unb64(encoded_signature)
        if not hmac.compare_digest(expected, supplied):
            raise GatewayServiceAuthError("invalid gateway service-token signature")

        try:
            payload = json.loads(_unb64(body))
            issued_at = int(payload["iat"])
            expires_at = int(payload["exp"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GatewayServiceAuthError("invalid gateway service-token claims") from exc

        current = int(time.time()) if now is None else int(now)
        if payload.get("iss") != self.ISSUER or payload.get("aud") != self.AUDIENCE:
            raise GatewayServiceAuthError("invalid gateway service-token authority")
        if issued_at > current + self.CLOCK_SKEW_SECONDS:
            raise GatewayServiceAuthError("gateway service token issued in the future")
        if expires_at <= current or expires_at - issued_at > self.MAX_TTL_SECONDS:
            raise GatewayServiceAuthError("gateway service token expired or overlong")

        expected_claims = {
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "method": method.upper(),
            "path": path,
        }
        if any(payload.get(key) != value for key, value in expected_claims.items()):
            raise GatewayServiceAuthError("gateway service token is not bound to this request")

        return GatewayServiceClaims(**expected_claims)
