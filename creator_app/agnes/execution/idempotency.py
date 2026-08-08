from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum


class IdempotencyState(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(slots=True)
class IdempotencyRecord:
    manifest_hash: str
    state: IdempotencyState
    result: dict[str, object] | None = None


class InMemoryIdempotencyStore:
    """Phase-1 development store. Deliberately marked non-production-safe."""

    production_safe = False

    def __init__(self) -> None:
        self._records: dict[str, IdempotencyRecord] = {}
        self._lock = asyncio.Lock()

    async def claim(self, key: str, manifest_hash: str) -> tuple[bool, IdempotencyRecord | None]:
        async with self._lock:
            existing = self._records.get(key)
            if existing is not None:
                return False, existing
            record = IdempotencyRecord(manifest_hash, IdempotencyState.RUNNING)
            self._records[key] = record
            return True, record

    async def complete(self, key: str, *, success: bool, result: dict[str, object]) -> None:
        async with self._lock:
            record = self._records.get(key)
            if record is None:
                return
            record.state = IdempotencyState.SUCCEEDED if success else IdempotencyState.FAILED
            record.result = result
