"""Small SQLite catalogue of Pinterest Pin references; image bytes are not copied."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class PinterestReferenceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=5) as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS pinterest_references (
                    pin_id TEXT PRIMARY KEY,
                    board_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    collected_at TEXT NOT NULL
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_pinterest_board ON pinterest_references(board_id)"
            )
            db.commit()

    def upsert(self, records: list[dict[str, object]]) -> int:
        now = datetime.now(UTC).isoformat()
        unique: dict[str, tuple[str, str, str, str]] = {}
        for record in records:
            pin_id = str(record.get("pin_id") or "")
            board_id = str(record.get("board_id") or "")
            if not pin_id or not board_id:
                continue
            payload = json.dumps(record, ensure_ascii=False, sort_keys=True)
            unique[pin_id] = (pin_id, board_id, payload, now)
        rows = list(unique.values())
        with sqlite3.connect(self.path, timeout=5) as db:
            db.executemany(
                """
                INSERT INTO pinterest_references(pin_id, board_id, payload_json, collected_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(pin_id) DO UPDATE SET
                    board_id=excluded.board_id,
                    payload_json=excluded.payload_json,
                    collected_at=excluded.collected_at
                """,
                rows,
            )
            db.commit()
        return len(rows)

    def list(self, *, limit: int = 50, offset: int = 0) -> list[dict[str, object]]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("limit must be 1-100 and offset must be non-negative")
        uri = f"file:{self.path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=5) as db:
            rows = db.execute(
                """
                SELECT payload_json FROM pinterest_references
                ORDER BY collected_at DESC, pin_id ASC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def summary(self) -> dict[str, int]:
        with sqlite3.connect(self.path, timeout=5) as db:
            total = int(db.execute("SELECT COUNT(*) FROM pinterest_references").fetchone()[0])
            boards = int(
                db.execute("SELECT COUNT(DISTINCT board_id) FROM pinterest_references").fetchone()[
                    0
                ]
            )
        return {"pin_reference_count": total, "board_count": boards}
