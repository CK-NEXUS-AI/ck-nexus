from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class IdempotencyState(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(slots=True)
class IdempotencyRecord:
    manifest_hash: str
    state: IdempotencyState
    result: dict[str, object] | None = None


class IdempotencyStore(Protocol):
    durable: bool
    distributed: bool
    production_safe: bool

    async def claim(
        self, key: str, manifest_hash: str
    ) -> tuple[bool, IdempotencyRecord | None]: ...

    async def complete(self, key: str, *, success: bool, result: dict[str, object]) -> None: ...


class InMemoryIdempotencyStore:
    """Phase-1 development store. Non-durable and non-production-safe."""

    durable = False
    distributed = False
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


class SQLiteIdempotencyStore:
    """Durable single-host idempotency store for local isolated development.

    This closes restart/retry gaps on one host, but is deliberately not marked
    production-safe because it does not coordinate multiple gateway/worker hosts.
    PostgreSQL/Redis remains the production target.
    """

    durable = True
    distributed = False
    production_safe = False

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path.parent.chmod(0o700)
        self._init_db()
        self.path.chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=FULL")
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS agnes_idempotency (
                    idem_key TEXT PRIMARY KEY,
                    manifest_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    result_json TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    async def claim(self, key: str, manifest_hash: str) -> tuple[bool, IdempotencyRecord | None]:
        return await asyncio.to_thread(self._claim_sync, key, manifest_hash)

    def _claim_sync(self, key: str, manifest_hash: str) -> tuple[bool, IdempotencyRecord | None]:
        with self._connect() as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                con.execute(
                    "INSERT INTO agnes_idempotency(idem_key, manifest_hash, state) VALUES(?,?,?)",
                    (key, manifest_hash, IdempotencyState.RUNNING.value),
                )
                con.execute("COMMIT")
                return True, IdempotencyRecord(manifest_hash, IdempotencyState.RUNNING)
            except sqlite3.IntegrityError:
                con.execute("ROLLBACK")
                row = con.execute(
                    "SELECT manifest_hash, state, result_json FROM agnes_idempotency "
                    "WHERE idem_key=?",
                    (key,),
                ).fetchone()
                if row is None:
                    return False, None
                result = json.loads(row["result_json"]) if row["result_json"] else None
                return False, IdempotencyRecord(
                    str(row["manifest_hash"]), IdempotencyState(str(row["state"])), result
                )

    async def complete(self, key: str, *, success: bool, result: dict[str, object]) -> None:
        await asyncio.to_thread(self._complete_sync, key, success, result)

    def _complete_sync(self, key: str, success: bool, result: dict[str, object]) -> None:
        with self._connect() as con:
            con.execute(
                """
                UPDATE agnes_idempotency
                   SET state=?, result_json=?, updated_at=CURRENT_TIMESTAMP
                 WHERE idem_key=?
                """,
                (
                    IdempotencyState.SUCCEEDED.value if success else IdempotencyState.FAILED.value,
                    json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                    key,
                ),
            )
