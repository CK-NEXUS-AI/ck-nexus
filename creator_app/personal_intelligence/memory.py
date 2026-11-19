"""Data-minimized semantic memory contracts for CK-NEXUS."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .consent import ConsentLedger, PersonalCapability


@dataclass(frozen=True, slots=True)
class MemoryItem:
    memory_id: str
    category: str
    summary: str
    source: str
    confidence: float
    created_at: datetime
    expires_at: datetime


class SemanticMemoryStore:
    """Stores short summaries only after explicit persistent-memory consent."""

    def __init__(self, consent: ConsentLedger, *, default_ttl_days: int = 90) -> None:
        if not 1 <= default_ttl_days <= 3650:
            raise ValueError("default_ttl_days must be between 1 and 3650")
        self._consent = consent
        self._default_ttl = timedelta(days=default_ttl_days)
        self._items: dict[str, MemoryItem] = {}

    def remember(
        self,
        *,
        category: str,
        summary: str,
        source: str,
        confidence: float = 1.0,
        ttl_days: int | None = None,
    ) -> MemoryItem:
        self._consent.require(PersonalCapability.MEMORY_STORE)
        normalized = " ".join(summary.split())
        if not normalized or len(normalized) > 500:
            raise ValueError("memory summary must be 1-500 characters")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        lifetime = self._default_ttl if ttl_days is None else timedelta(days=ttl_days)
        if lifetime <= timedelta(0) or lifetime > timedelta(days=3650):
            raise ValueError("memory TTL must be between 1 and 3650 days")
        created = datetime.now(UTC)
        material = f"{category}|{normalized}|{source}|{created.isoformat()}".encode()
        item = MemoryItem(
            memory_id=f"mem-{hashlib.sha256(material).hexdigest()[:20]}",
            category=category.strip().lower(),
            summary=normalized,
            source=source.strip(),
            confidence=confidence,
            created_at=created,
            expires_at=created + lifetime,
        )
        self._items[item.memory_id] = item
        return item

    def active(self, now: datetime | None = None) -> tuple[MemoryItem, ...]:
        current = now or datetime.now(UTC)
        return tuple(item for item in self._items.values() if item.expires_at > current)

    def delete(self, memory_id: str) -> bool:
        return self._items.pop(memory_id, None) is not None

    def purge_expired(self, now: datetime | None = None) -> int:
        current = now or datetime.now(UTC)
        expired = [key for key, item in self._items.items() if item.expires_at <= current]
        for key in expired:
            del self._items[key]
        return len(expired)

    def export(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in self.active():
            payload = asdict(item)
            payload["created_at"] = item.created_at.isoformat()
            payload["expires_at"] = item.expires_at.isoformat()
            result.append(payload)
        return result
