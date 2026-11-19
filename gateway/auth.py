from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .errors import GatewayError
from .identity import GatewayIdentity


class TokenDecoder(Protocol):
    def decode(self, token: str, *, audience: str) -> dict[str, object]: ...


@dataclass(slots=True)
class PyJWTDecoder:
    public_key: str
    algorithm: str
    issuer: str

    def decode(self, token: str, *, audience: str) -> dict[str, object]:
        if not self.public_key:
            raise GatewayError("AUTH_NOT_CONFIGURED", "Authentication is unavailable.", 503)
        try:
            import jwt

            return jwt.decode(
                token,
                self.public_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=audience,
                options={"require": ["exp", "iat", "sub", "iss", "aud", "tenant_id"]},
            )
        except GatewayError:
            raise
        except Exception:
            raise GatewayError("UNAUTHORIZED", "Invalid or expired access token.", 401) from None


def extract_bearer(header: str | None) -> str:
    if not header or not header.startswith("Bearer "):
        raise GatewayError("UNAUTHORIZED", "Bearer authentication is required.", 401)
    token = header[7:].strip()
    if not token:
        raise GatewayError("UNAUTHORIZED", "Bearer authentication is required.", 401)
    return token


def authenticate(
    authorization: str | None,
    *,
    decoder: TokenDecoder,
    audience: str,
) -> GatewayIdentity:
    token = extract_bearer(authorization)
    claims = decoder.decode(token, audience=audience)
    try:
        return GatewayIdentity.from_claims(claims, audience=audience)
    except ValueError:
        raise GatewayError("UNAUTHORIZED", "Access token identity is incomplete.", 401) from None


def authorize(identity: GatewayIdentity, required: frozenset[str]) -> None:
    if not required.issubset(identity.permissions):
        raise GatewayError("FORBIDDEN", "Insufficient permission for this route.", 403)
