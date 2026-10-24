"""Durable, deduplicated n8n intelligence ledger."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from .models import N8NExecutionEvent


class N8NIntelligenceStore:
    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        path = Path(self.database)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        path.chmod(0o600)
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS n8n_events (
                    event_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    repeat_count INTEGER NOT NULL DEFAULT 1,
                    first_seen REAL NOT NULL DEFAULT (unixepoch('now')),
                    last_seen REAL NOT NULL DEFAULT (unixepoch('now'))
                );
                CREATE TABLE IF NOT EXISTS n8n_checkpoint (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    value TEXT
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def record_event(self, event: N8NExecutionEvent) -> tuple[bool, int]:
        payload = json.dumps(
            event.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT repeat_count FROM n8n_events WHERE event_id=?", (event.event_id,)
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO n8n_events(event_id,execution_id,event_json) VALUES(?,?,?)",
                    (event.event_id, event.execution_id, payload),
                )
                connection.commit()
                return True, 1
            count = int(row["repeat_count"]) + 1
            connection.execute(
                "UPDATE n8n_events SET repeat_count=?, last_seen=unixepoch('now') WHERE event_id=?",
                (count, event.event_id),
            )
            connection.commit()
            return False, count

    def checkpoint(self) -> str | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT value FROM n8n_checkpoint WHERE id=1").fetchone()
        return str(row["value"]) if row and row["value"] is not None else None

    def set_checkpoint(self, value: str) -> None:
        if not value.strip():
            raise ValueError("checkpoint must not be empty")
        with closing(self._connect()) as connection:
            connection.execute(
                "INSERT INTO n8n_checkpoint(id,value) VALUES(1,?) "
                "ON CONFLICT(id) DO UPDATE SET value=excluded.value",
                (value,),
            )
