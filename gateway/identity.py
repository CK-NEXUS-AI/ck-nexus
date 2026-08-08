from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GatewayIdentity:
    actor_id: str
    tenant_id: str
    roles: frozenset[str]
    permissions: frozenset[str]
    issuer: str
    audience: str

    @classmethod
    def from_claims(cls, claims: dict[str, object], *, audience: str) -> "GatewayIdentity":
        actor = str(claims.get("sub") or "")
        tenant = str(claims.get("tenant_id") or "")
        if not actor or not tenant:
            raise ValueError("subject and tenant_id claims are required")
        roles = frozenset(str(item) for item in (claims.get("roles") or []))
        permissions = frozenset(str(item) for item in (claims.get("permissions") or []))
        return cls(
            actor_id=actor,
            tenant_id=tenant,
            roles=roles,
            permissions=permissions,
            issuer=str(claims.get("iss") or ""),
            audience=audience,
        )
