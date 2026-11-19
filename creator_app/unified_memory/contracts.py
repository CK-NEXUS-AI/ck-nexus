"""Authority-aware memory contracts for CK-NEXUS Unified Memory V2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import IntEnum, StrEnum

from creator_app.privacy_firewall import DataClassification


class MemoryKind(StrEnum):
    WORKING = "working"
    SESSION = "session"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PREFERENCE = "preference"
    OPERATIONAL = "operational"


class MemoryAuthority(IntEnum):
    INFERRED = 10
    REPEATED_BEHAVIOR = 20
    VERIFIED_SOURCE = 30
    EXPLICIT_USER = 40
    SYSTEM_AUTHORITY = 50


class MemoryStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DELETED = "deleted"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    memory_id: str
    tenant_id: str
    user_id: str
    kind: MemoryKind
    key: str
    statement: str
    source: str
    source_id: str
    authority: MemoryAuthority
    confidence: float
    classification: DataClassification
    created_at: datetime
    expires_at: datetime | None = None
    consent_id: str | None = None
    supersedes: str | None = None
    status: MemoryStatus = MemoryStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.memory_id.strip():
            raise ValueError("memory_id must not be empty")
        if not self.tenant_id.strip() or not self.user_id.strip():
            raise ValueError("tenant_id and user_id must not be empty")
        if not self.key.strip() or not self.statement.strip():
            raise ValueError("key and statement must not be empty")
        if not self.source.strip() or not self.source_id.strip():
            raise ValueError("source and source_id must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")

    @property
    def expired(self) -> bool:
        return self.expires_at is not None and datetime.now(UTC) >= self.expires_at
