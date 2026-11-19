"""Durable SQLite queue and checkpoints for restart-safe control-plane work."""

from __future__ import annotations

import json
import math
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any


class TaskStore:
    """Small local queue; it stores task data, never provider credentials."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS control_plane_tasks (
                    job_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (state IN ('queued','running','completed','failed')),
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    worker_id TEXT,
                    lease_until REAL,
                    lease_token TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    checkpoint_json TEXT,
                    result_json TEXT,
                    error_text TEXT
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(control_plane_tasks)").fetchall()
            }
            if "lease_token" not in columns:
                connection.execute("ALTER TABLE control_plane_tasks ADD COLUMN lease_token TEXT")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_control_plane_tasks_queue "
                "ON control_plane_tasks(state, created_at)"
            )
        Path(self.database).chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def enqueue(self, job_id: str, payload: dict[str, Any]) -> None:
        if not job_id.strip():
            raise ValueError("job_id must not be empty")
        now = time.time()
        try:
            with closing(self._connect()) as connection:
                connection.execute(
                    "INSERT INTO control_plane_tasks "
                    "(job_id,payload_json,state,created_at,updated_at) VALUES (?,?, 'queued',?,?)",
                    (job_id, self._json(payload), now, now),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"job_id already exists: {job_id}") from exc

    def enqueue_many(self, tasks: list[tuple[str, dict[str, Any]]]) -> None:
        """Atomically enqueue a bounded batch of tasks or insert none of them."""
        if not tasks:
            raise ValueError("tasks must not be empty")
        seen: set[str] = set()
        rows: list[tuple[str, str, float, float]] = []
        now = time.time()
        for job_id, payload in tasks:
            if not isinstance(job_id, str) or not job_id.strip():
                raise ValueError("job_id must not be empty")
            if job_id in seen:
                raise ValueError(f"job_id duplicated in batch: {job_id}")
            if not isinstance(payload, dict):
                raise ValueError("task payload must be an object")
            seen.add(job_id)
            rows.append((job_id, self._json(payload), now, now))
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.executemany(
                    "INSERT INTO control_plane_tasks "
                    "(job_id,payload_json,state,created_at,updated_at) "
                    "VALUES (?, ?, 'queued', ?, ?)",
                    rows,
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise ValueError("job_id already exists in batch") from exc

    def peek_next(self) -> dict[str, Any] | None:
        """Return the oldest queued task without claiming or mutating it."""
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM control_plane_tasks WHERE state='queued' "
                "ORDER BY created_at, job_id LIMIT 1"
            ).fetchone()
        return dict(row) if row is not None else None

    def has_open_tasks(self) -> bool:
        """Return whether any task is queued or running, without mutating the queue."""
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT 1 FROM control_plane_tasks WHERE state IN ('queued','running') LIMIT 1"
            ).fetchone()
        return row is not None

    def claim_next(
        self, worker_id: str, *, lease_seconds: float = 300, job_id: str | None = None
    ) -> dict[str, Any] | None:
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        if (
            isinstance(lease_seconds, bool)
            or not isinstance(lease_seconds, (int, float))
            or not math.isfinite(lease_seconds)
            or not 0 <= lease_seconds <= 86400
        ):
            raise ValueError("lease_seconds must be finite and between 0 and 86400")
        now = time.time()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            if job_id is None:
                row = connection.execute(
                    "SELECT job_id FROM control_plane_tasks WHERE state='queued' "
                    "ORDER BY created_at, job_id LIMIT 1"
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT job_id FROM control_plane_tasks WHERE state='queued' AND job_id=?",
                    (job_id,),
                ).fetchone()
            if row is None:
                connection.commit()
                return None
            job_id = row["job_id"]
            lease_token = secrets.token_urlsafe(32)
            connection.execute(
                "UPDATE control_plane_tasks SET state='running', worker_id=?, lease_until=?, "
                "lease_token=?, attempts=attempts+1, updated_at=? "
                "WHERE job_id=? AND state='queued'",
                (worker_id, now + max(0.0, lease_seconds), lease_token, now, job_id),
            )
            claimed = connection.execute(
                "SELECT * FROM control_plane_tasks WHERE job_id=?", (job_id,)
            ).fetchone()
            connection.commit()
        return dict(claimed) if claimed is not None else None

    def save_checkpoint(
        self,
        job_id: str,
        checkpoint: dict[str, Any],
        *,
        worker_id: str,
        lease_token: str,
    ) -> None:
        if not worker_id.strip() or not lease_token.strip():
            raise ValueError("worker_id and lease_token must not be empty")
        now = time.time()
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "UPDATE control_plane_tasks SET checkpoint_json=?, updated_at=? "
                "WHERE job_id=? AND state='running' AND lease_until>? "
                "AND worker_id=? AND lease_token=?",
                (self._json(checkpoint), now, job_id, now, worker_id, lease_token),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"job is not running with a valid lease: {job_id}")

    def finish(
        self,
        job_id: str,
        *,
        success: bool,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        worker_id: str,
        lease_token: str,
    ) -> None:
        if not worker_id.strip() or not lease_token.strip():
            raise ValueError("worker_id and lease_token must not be empty")
        state = "completed" if success else "failed"
        now = time.time()
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "UPDATE control_plane_tasks SET state=?, result_json=?, error_text=?, "
                "worker_id=NULL, lease_until=NULL, lease_token=NULL, updated_at=? "
                "WHERE job_id=? AND state='running' AND lease_until>? "
                "AND worker_id=? AND lease_token=?",
                (
                    state,
                    self._json(result) if result is not None else None,
                    error,
                    now,
                    job_id,
                    now,
                    worker_id,
                    lease_token,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError(f"job is not running with a valid lease: {job_id}")

    def requeue_expired(self, *, max_attempts: int = 3) -> int:
        """Requeue expired leases within a bounded retry budget.

        Returns the number of jobs requeued. Jobs that have exhausted the budget
        are marked failed and are deliberately not included in the return value.
        """
        if not 1 <= max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        now = time.time()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE control_plane_tasks SET state='failed', worker_id=NULL, "
                "lease_until=NULL, lease_token=NULL, "
                "error_text=COALESCE(error_text, ?), updated_at=? "
                "WHERE state='running' AND lease_until<=? AND attempts>=?",
                ("lease expired; retry budget exhausted", now, now, max_attempts),
            )
            cursor = connection.execute(
                "UPDATE control_plane_tasks SET state='queued', worker_id=NULL, "
                "lease_until=NULL, lease_token=NULL, updated_at=? "
                "WHERE state='running' AND lease_until<=? AND attempts<?",
                (now, now, max_attempts),
            )
            connection.commit()
            return cursor.rowcount

    def get(self, job_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM control_plane_tasks WHERE job_id=?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item.pop("lease_token", None)
        return item
