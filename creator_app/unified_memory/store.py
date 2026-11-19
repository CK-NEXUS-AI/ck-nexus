"""Minimal authority-aware memory store with explicit supersession and deletion."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime

from creator_app.privacy_firewall import DataClassification

from .contracts import MemoryRecord, MemoryStatus


class MemoryPolicyError(PermissionError):
    """Raised when a record violates CK-NEXUS memory policy."""


class UnifiedMemoryStore:
    """In-memory reference implementation of the Unified Memory V2 contract."""

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    def add(self, record: MemoryRecord) -> MemoryRecord:
        if record.classification in {
            DataClassification.SECRET,
            DataClassification.REGULATED,
        }:
            raise MemoryPolicyError(
                "secret or regulated content is not eligible for semantic memory"
            )
        if record.memory_id in self._records:
            raise ValueError("memory_id already exists")

        active = self._active_for_key(record.tenant_id, record.user_id, record.key)
        if active is not None:
            if active.authority > record.authority:
                raise MemoryPolicyError("lower-authority memory cannot supersede active memory")
            self._records[active.memory_id] = replace(active, status=MemoryStatus.SUPERSEDED)
            record = replace(record, supersedes=active.memory_id)

        self._records[record.memory_id] = record
        return record

    def get(self, memory_id: str) -> MemoryRecord | None:
        record = self._records.get(memory_id)
        if record is None:
            return None
        if record.expired and record.status == MemoryStatus.ACTIVE:
            expired = replace(record, status=MemoryStatus.EXPIRED)
            self._records[memory_id] = expired
            return expired
        return record

    def active(
        self,
        *,
        tenant_id: str,
        user_id: str,
        kind: str | None = None,
    ) -> tuple[MemoryRecord, ...]:
        result: list[MemoryRecord] = []
        for memory_id in tuple(self._records):
            record = self.get(memory_id)
            if record is None or record.status != MemoryStatus.ACTIVE:
                continue
            if record.tenant_id != tenant_id or record.user_id != user_id:
                continue
            if kind is not None and record.kind.value != kind:
                continue
            result.append(record)
        return tuple(sorted(result, key=lambda item: item.created_at))

    def delete(self, memory_id: str, *, tenant_id: str, user_id: str) -> bool:
        record = self._records.get(memory_id)
        if record is None:
            return False
        if record.tenant_id != tenant_id or record.user_id != user_id:
            return False
        self._records[memory_id] = replace(
            record,
            status=MemoryStatus.DELETED,
            statement="<deleted>",
        )
        return True

    def delete_all(self, *, tenant_id: str, user_id: str) -> int:
        deleted = 0
        for memory_id, record in tuple(self._records.items()):
            if (
                record.tenant_id == tenant_id
                and record.user_id == user_id
                and record.status != MemoryStatus.DELETED
            ):
                self._records[memory_id] = replace(
                    record,
                    status=MemoryStatus.DELETED,
                    statement="<deleted>",
                )
                deleted += 1
        return deleted

    def export(self, *, tenant_id: str, user_id: str) -> tuple[dict[str, object], ...]:
        exported: list[dict[str, object]] = []
        for record in self.active(tenant_id=tenant_id, user_id=user_id):
            exported.append(
                {
                    "memory_id": record.memory_id,
                    "kind": record.kind.value,
                    "key": record.key,
                    "statement": record.statement,
                    "source": record.source,
                    "source_id": record.source_id,
                    "authority": int(record.authority),
                    "confidence": record.confidence,
                    "classification": record.classification.value,
                    "created_at": record.created_at.isoformat(),
                    "expires_at": record.expires_at.isoformat() if record.expires_at else None,
                    "consent_id": record.consent_id,
                    "supersedes": record.supersedes,
                    "status": record.status.value,
                }
            )
        return tuple(exported)

    def provenance_digest(self, *, tenant_id: str, user_id: str) -> str:
        material = "\n".join(
            f"{item['memory_id']}:{item['source']}:{item['source_id']}:{item['status']}"
            for item in self.export(tenant_id=tenant_id, user_id=user_id)
        ).encode()
        return hashlib.sha256(material).hexdigest()

    def _active_for_key(self, tenant_id: str, user_id: str, key: str) -> MemoryRecord | None:
        candidates = [
            record
            for record in self._records.values()
            if record.tenant_id == tenant_id
            and record.user_id == user_id
            and record.key == key
            and record.status == MemoryStatus.ACTIVE
            and not record.expired
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: (item.authority, item.created_at))


def memory_id_for(*, tenant_id: str, user_id: str, key: str, source_id: str) -> str:
    material = f"{tenant_id}:{user_id}:{key}:{source_id}".encode()
    return f"mem-{hashlib.sha256(material).hexdigest()[:20]}"


def utc_now() -> datetime:
    return datetime.now(UTC)
