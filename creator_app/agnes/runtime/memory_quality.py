from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class MemoryQualityStatus(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIED = "UNVERIFIED"


@dataclass(slots=True)
class MemoryQualityEntry:
    memory_id: str
    observed_at: datetime
    source_digest: str | None = None
    expires_at: datetime | None = None
    contradictory_with: list[str] = field(default_factory=list)
    verified_by: str | None = None

    def status(self, now: datetime | None = None) -> MemoryQualityStatus:
        now = now or datetime.now(timezone.utc)
        if self.contradictory_with:
            return MemoryQualityStatus.CONTRADICTED
        if self.expires_at is not None and now >= self.expires_at:
            return MemoryQualityStatus.STALE
        if not self.source_digest or not self.verified_by:
            return MemoryQualityStatus.UNVERIFIED
        return MemoryQualityStatus.FRESH
