from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field


class EvidenceRecord(BaseModel):
    sequence: int = Field(ge=1)
    event_type: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    payload_digest: str = Field(min_length=64, max_length=64)
    previous_hash: str = Field(min_length=64, max_length=64)
    record_hash: str = Field(min_length=64, max_length=64)
    created_at: datetime


class HashLinkedEvidenceStore:
    """Append-only JSONL evidence chain for development verification.

    Payload contents are not persisted here; only caller-provided payload digests are stored.
    Each record commits to the previous record hash and is fsync'd before returning.
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, path: Path) -> None:
        self.path = path

    @staticmethod
    def payload_digest(payload: object) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _record_hash(
        *,
        sequence: int,
        event_type: str,
        subject: str,
        payload_digest: str,
        previous_hash: str,
        created_at: datetime,
    ) -> str:
        canonical = {
            "created_at": created_at.astimezone(UTC).isoformat(),
            "event_type": event_type,
            "payload_digest": payload_digest,
            "previous_hash": previous_hash,
            "sequence": sequence,
            "subject": subject,
        }
        encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def read_all(self) -> list[EvidenceRecord]:
        if not self.path.exists():
            return []
        records: list[EvidenceRecord] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(EvidenceRecord.model_validate_json(line))
        return records

    def append(
        self,
        *,
        event_type: str,
        subject: str,
        payload_digest: str,
        created_at: datetime,
    ) -> EvidenceRecord:
        if created_at.tzinfo is None:
            raise ValueError("evidence timestamps must be timezone-aware")
        records = self.read_all()
        previous_hash = records[-1].record_hash if records else self.GENESIS_HASH
        sequence = len(records) + 1
        normalized = created_at.astimezone(UTC)
        record_hash = self._record_hash(
            sequence=sequence,
            event_type=event_type,
            subject=subject,
            payload_digest=payload_digest,
            previous_hash=previous_hash,
            created_at=normalized,
        )
        record = EvidenceRecord(
            sequence=sequence,
            event_type=event_type,
            subject=subject,
            payload_digest=payload_digest,
            previous_hash=previous_hash,
            record_hash=record_hash,
            created_at=normalized,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(fd, (record.model_dump_json() + "\n").encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        return record

    def verify_chain(self) -> bool:
        records = self.read_all()
        previous_hash = self.GENESIS_HASH
        for expected_sequence, record in enumerate(records, start=1):
            if record.sequence != expected_sequence or record.previous_hash != previous_hash:
                return False
            expected_hash = self._record_hash(
                sequence=record.sequence,
                event_type=record.event_type,
                subject=record.subject,
                payload_digest=record.payload_digest,
                previous_hash=record.previous_hash,
                created_at=record.created_at,
            )
            if record.record_hash != expected_hash:
                return False
            previous_hash = record.record_hash
        return True
