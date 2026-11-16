from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass


class IdentityError(PermissionError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(value: str) -> bytes:
    decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if _b64(decoded) != value:
        raise IdentityError("non-canonical base64url token")
    return decoded


@dataclass(frozen=True, slots=True)
class CallerIdentity:
    service_id: str
    agent_id: str
    role: str


class IdentityVerifier:
    """HMAC service-token verifier. The authority derives agent identity from token claims."""

    MAX_TOKEN_BYTES = 8192
    MAX_TTL_SECONDS = 900
    CLOCK_SKEW_SECONDS = 60

    def __init__(self, secret: bytes, *, issuer: str = "ck-nexus"):
        if not isinstance(secret, bytes) or len(secret) < 32:
            raise ValueError("identity secret must be at least 32 bytes")
        if not isinstance(issuer, str) or not issuer.strip():
            raise ValueError("identity issuer is required")
        self.secret, self.issuer = secret, issuer

    def issue(
        self, *, service_id: str, agent_id: str, role: str = "agent", ttl_seconds: int = 300
    ) -> str:
        for name, value in (("service_id", service_id), ("agent_id", agent_id), ("role", role)):
            if not isinstance(value, str) or not value.strip() or len(value) > 160:
                raise ValueError(f"{name} must be a non-empty string of at most 160 characters")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
            raise ValueError("identity token TTL must be an integer")
        if not 1 <= ttl_seconds <= self.MAX_TTL_SECONDS:
            raise ValueError("identity token TTL is outside policy")
        now = int(time.time())
        payload = {
            "iss": self.issuer,
            "service_id": service_id,
            "agent_id": agent_id,
            "role": role,
            "iat": now,
            "exp": now + ttl_seconds,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        body = _b64(raw)
        sig = _b64(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
        return f"{body}.{sig}"

    def verify(self, token: str) -> CallerIdentity:
        if not isinstance(token, str) or not token or len(token) > self.MAX_TOKEN_BYTES:
            raise IdentityError("invalid service token size")
        try:
            body, sig = token.split(".", 1)
            if not body or not sig or "." in sig:
                raise IdentityError("malformed service token")
            supplied_signature = _unb64(sig)
            raw_payload = _unb64(body)
            expected = hmac.new(self.secret, body.encode(), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, supplied_signature):
                raise IdentityError("invalid service token signature")
            data = json.loads(raw_payload)
        except IdentityError:
            raise
        except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise IdentityError("malformed service token") from exc

        if not isinstance(data, dict):
            raise IdentityError("service token claims must be an object")
        if data.get("iss") != self.issuer:
            raise IdentityError("invalid token issuer")
        issued_at = data.get("iat")
        expires_at = data.get("exp")
        now = int(time.time())
        if (
            isinstance(issued_at, bool)
            or not isinstance(issued_at, int)
            or isinstance(expires_at, bool)
            or not isinstance(expires_at, int)
        ):
            raise IdentityError("invalid service token timestamps")
        if issued_at > now + self.CLOCK_SKEW_SECONDS:
            raise IdentityError("service token issued in the future")
        if expires_at <= now or expires_at <= issued_at:
            raise IdentityError("service token expired or invalid")
        if expires_at - issued_at > self.MAX_TTL_SECONDS:
            raise IdentityError("service token lifetime exceeds policy")

        service_id = data.get("service_id")
        agent_id = data.get("agent_id")
        role = data.get("role", "agent")
        if any(
            not isinstance(value, str) or not value.strip() or len(value) > 160
            for value in (service_id, agent_id, role)
        ):
            raise IdentityError("service token identity claims are invalid")
        return CallerIdentity(service_id, agent_id, role)
