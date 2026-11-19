"""Granular, revocable consent contracts for CK-NEXUS personal intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class PersonalCapability(StrEnum):
    """Personal-data capabilities that require explicit authorization."""

    GMAIL_READ = "gmail.read"
    GMAIL_SEND = "gmail.send"
    PROFILE_LEARN = "profile.learn"
    MEMORY_STORE = "memory.store"
    PROACTIVE_NOTIFY = "proactive.notify"
    CROSS_CHANNEL_SYNC = "cross_channel.sync"


class ConsentRequired(PermissionError):
    """Raised when a personal-data capability has no active consent grant."""


@dataclass(frozen=True, slots=True)
class ConsentGrant:
    capability: PersonalCapability
    purpose: str
    granted_at: datetime
    expires_at: datetime | None = None
    source: str = "explicit_user_action"

    def active(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return self.expires_at is None or current < self.expires_at


class ConsentLedger:
    """In-memory consent authority with explicit grant/revoke semantics.

    Persistence is intentionally left to the CK-NEXUS authority layer so this
    component cannot silently create durable consent by itself.
    """

    def __init__(self) -> None:
        self._grants: dict[PersonalCapability, ConsentGrant] = {}

    def grant(
        self,
        capability: PersonalCapability,
        *,
        purpose: str,
        expires_at: datetime | None = None,
        source: str = "explicit_user_action",
    ) -> ConsentGrant:
        normalized = purpose.strip()
        if not normalized:
            raise ValueError("consent purpose must not be empty")
        grant = ConsentGrant(
            capability=capability,
            purpose=normalized,
            granted_at=datetime.now(UTC),
            expires_at=expires_at,
            source=source,
        )
        self._grants[capability] = grant
        return grant

    def revoke(self, capability: PersonalCapability) -> bool:
        return self._grants.pop(capability, None) is not None

    def allowed(self, capability: PersonalCapability) -> bool:
        grant = self._grants.get(capability)
        return grant is not None and grant.active()

    def require(self, capability: PersonalCapability) -> ConsentGrant:
        grant = self._grants.get(capability)
        if grant is None or not grant.active():
            raise ConsentRequired(f"active consent required for {capability.value}")
        return grant

    def snapshot(self) -> dict[str, dict[str, str | None | bool]]:
        return {
            capability.value: {
                "allowed": grant.active(),
                "purpose": grant.purpose,
                "source": grant.source,
                "granted_at": grant.granted_at.isoformat(),
                "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
            }
            for capability, grant in sorted(self._grants.items(), key=lambda item: item[0].value)
        }
