"""Evidence-aware temporal memory contracts for AGNES."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    memory_id: str
    kind: str
    content: str
    source: str
    confidence: float
    observed_at: datetime
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    supersedes: str | None = None
    evidence_refs: tuple[str, ...] = ()

    def is_valid_at(self, when: datetime) -> bool:
        if self.valid_from and when < self.valid_from:
            return False
        return not (self.valid_until and when >= self.valid_until)


class TemporalMemory:
    """Append-only memory with explicit supersession; no silent overwrite."""

    def __init__(self) -> None:
        self._records: list[MemoryRecord] = []

    def append(self, record: MemoryRecord) -> None:
        if not 0.0 <= record.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if record.supersedes and not any(
            item.memory_id == record.supersedes for item in self._records
        ):
            raise ValueError("superseded memory does not exist")
        if any(item.memory_id == record.memory_id for item in self._records):
            raise ValueError("memory_id already exists")
        self._records.append(record)

    def active(
        self,
        *,
        kind: str | None = None,
        when: datetime | None = None,
    ) -> tuple[MemoryRecord, ...]:
        now = when or datetime.now(UTC)
        superseded = {item.supersedes for item in self._records if item.supersedes}
        return tuple(
            item
            for item in self._records
            if item.memory_id not in superseded
            and item.is_valid_at(now)
            and (kind is None or item.kind == kind)
        )

    def history(self) -> tuple[MemoryRecord, ...]:
        return tuple(self._records)
