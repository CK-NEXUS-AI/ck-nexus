from __future__ import annotations

from datetime import datetime, timezone
from .models import EvidenceRecord, EvidenceStatus, VerificationLevel


class EvidenceConflict(ValueError):
    pass


class AppendOnlyEvidenceStore:
    """In-memory prototype. Records are append-only and immutable."""

    def __init__(self) -> None:
        self._records: list[EvidenceRecord] = []
        self._ids: set[str] = set()

    def append(self, record: EvidenceRecord) -> None:
        if record.evidence_id in self._ids:
            raise EvidenceConflict(f"duplicate evidence_id: {record.evidence_id}")
        if record.supersedes and record.supersedes not in self._ids:
            raise EvidenceConflict("supersedes must reference an existing evidence record")
        self._records.append(record)
        self._ids.add(record.evidence_id)

    def all(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records)

    def by_control(self, control_id: str) -> tuple[EvidenceRecord, ...]:
        return tuple(r for r in self._records if r.control_id == control_id)

    def current(self, control_id: str, *, now: datetime | None = None) -> EvidenceRecord | None:
        matches = self.by_control(control_id)
        if not matches:
            return None
        record = matches[-1]
        now = now or datetime.now(timezone.utc)
        if record.stale_after and record.stale_after <= now:
            return record.model_copy(update={"status": EvidenceStatus.EXPIRED})
        return record


def same_subject(records: tuple[EvidenceRecord, ...]) -> bool:
    return len({r.subject for r in records}) <= 1


def can_relabel_verification(source: VerificationLevel, target: VerificationLevel) -> bool:
    """Fail closed: a label change alone can never promote evidence."""
    return source == target
