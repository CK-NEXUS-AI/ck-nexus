from __future__ import annotations
import base64, hashlib, hmac, json, time
from dataclasses import dataclass

class IdentityError(PermissionError): pass

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
    def __init__(self, secret: bytes, *, issuer: str = "ck-nexus"):
        if len(secret) < 32: raise ValueError("identity secret must be at least 32 bytes")
        self.secret, self.issuer = secret, issuer

    def issue(self, *, service_id: str, agent_id: str, role: str = "agent", ttl_seconds: int = 300) -> str:
        now = int(time.time())
        payload = {"iss": self.issuer, "service_id": service_id, "agent_id": agent_id, "role": role, "iat": now, "exp": now + ttl_seconds}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        body = _b64(raw); sig = _b64(hmac.new(self.secret, body.encode(), hashlib.sha256).digest())
        return f"{body}.{sig}"

    def verify(self, token: str) -> CallerIdentity:
        try: body, sig = token.split(".", 1)
        except ValueError as exc: raise IdentityError("malformed service token") from exc
        expected = hmac.new(self.secret, body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(sig)): raise IdentityError("invalid service token signature")
        data = json.loads(_unb64(body))
        if data.get("iss") != self.issuer: raise IdentityError("invalid token issuer")
        if int(data.get("exp", 0)) <= int(time.time()): raise IdentityError("service token expired")
        return CallerIdentity(str(data["service_id"]), str(data["agent_id"]), str(data.get("role", "agent")))
