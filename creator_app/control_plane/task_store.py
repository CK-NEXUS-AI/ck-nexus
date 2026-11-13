"""Durable SQLite queue and checkpoints for restart-safe control-plane work."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

COMPLETION_CAPABILITY_ID = "control_plane.task.complete"


class TaskStore:
    """Small local queue; it stores task data, never provider credentials."""

    def __init__(self, database: str | Path, *, grant_secret: bytes | None = None) -> None:
        self.database = str(database)
        configured_secret = os.environ.get("CKNEXUS_CAPABILITY_GRANT_SECRET", "")
        self.grant_secret = (
            grant_secret if grant_secret is not None else configured_secret.encode("utf-8")
        )
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS control_plane_tasks (
                    job_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (
                        state IN ('queued','running','awaiting_approval','completed','failed')
                    ),
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
            schema_row = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='control_plane_tasks'"
            ).fetchone()
            if schema_row and "awaiting_approval" not in str(schema_row["sql"]):
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("DROP INDEX IF EXISTS idx_control_plane_tasks_queue")
                connection.execute(
                    "ALTER TABLE control_plane_tasks RENAME TO control_plane_tasks_legacy"
                )
                connection.execute("""
                    CREATE TABLE control_plane_tasks (
                        job_id TEXT PRIMARY KEY, payload_json TEXT NOT NULL,
                        state TEXT NOT NULL CHECK (
                            state IN ('queued','running','awaiting_approval','completed','failed')
                        ),
                        created_at REAL NOT NULL, updated_at REAL NOT NULL, worker_id TEXT,
                        lease_until REAL, lease_token TEXT, attempts INTEGER NOT NULL DEFAULT 0,
                        checkpoint_json TEXT, result_json TEXT, error_text TEXT
                    )
                """)
                connection.execute(
                    "INSERT INTO control_plane_tasks "
                    "SELECT job_id,payload_json,state,created_at,updated_at,worker_id,lease_until,"
                    "lease_token,attempts,checkpoint_json,result_json,error_text "
                    "FROM control_plane_tasks_legacy"
                )
                connection.execute("DROP TABLE control_plane_tasks_legacy")
                connection.execute(
                    "CREATE INDEX idx_control_plane_tasks_queue "
                    "ON control_plane_tasks(state, created_at)"
                )
                connection.commit()
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
                "SELECT 1 FROM control_plane_tasks "
                "WHERE state IN ('queued','running','awaiting_approval') LIMIT 1"
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
        evidence_reference: str | None = None,
        approver_token: str | None = None,
        execution_grant: dict[str, Any] | None = None,
        worker_id: str,
        lease_token: str,
    ) -> None:
        """Finish a task, consuming a task-bound Core/L3 grant atomically.

        Identity tokens authenticate callers but never authorize completion. The
        signed one-time grant, its task/evidence binding, and the task transition
        are checked and committed in this same SQLite transaction. Therefore the
        AuthorityStore grants/evidence tables MUST share this database file.
        """
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        if not isinstance(lease_token, str) or not lease_token.strip():
            raise ValueError("lease_token must not be empty")
        now = time.time()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT checkpoint_json FROM control_plane_tasks "
                "WHERE job_id=? AND state='running' "
                "AND lease_until>? AND worker_id=? AND lease_token=?",
                (job_id, now, worker_id, lease_token),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise ValueError(f"job is not running with a valid lease: {job_id}")
            if success:
                completed_result = dict(result or {})
                completed_result["evidence_reference"] = evidence_reference
                approver_id = self._consume_completion_grant(
                    connection,
                    job_id=job_id,
                    evidence_reference=evidence_reference,
                    completion_result=completed_result,
                    execution_grant=execution_grant,
                )
                completed_result["approver_id"] = approver_id
                try:
                    checkpoint = json.loads(row["checkpoint_json"] or "{}")
                except (TypeError, json.JSONDecodeError):
                    checkpoint = {}
                if not isinstance(checkpoint, dict):
                    checkpoint = {}
                checkpoint.update(
                    {
                        "state": "completed",
                        "evidence_reference": evidence_reference,
                        "approver_id": approver_id,
                    }
                )
                cursor = connection.execute(
                    "UPDATE control_plane_tasks SET state='completed', "
                    "result_json=?, checkpoint_json=?, "
                    "error_text=NULL, worker_id=NULL, lease_until=NULL, "
                    "lease_token=NULL, updated_at=? "
                    "WHERE job_id=? AND state='running' AND lease_until>? "
                    "AND worker_id=? AND lease_token=?",
                    (
                        self._json(completed_result),
                        self._json(checkpoint),
                        now,
                        job_id,
                        now,
                        worker_id,
                        lease_token,
                    ),
                )
                if cursor.rowcount != 1:
                    connection.rollback()
                    raise ValueError(f"job is not running with a valid lease: {job_id}")
                connection.commit()
                return
            cursor = connection.execute(
                "UPDATE control_plane_tasks SET state='failed', result_json=?, error_text=?, "
                "worker_id=NULL, lease_until=NULL, lease_token=NULL, updated_at=? "
                "WHERE job_id=? AND state='running' AND lease_until>? "
                "AND worker_id=? AND lease_token=?",
                (
                    self._json(dict(result or {})) if result is not None else None,
                    error,
                    now,
                    job_id,
                    now,
                    worker_id,
                    lease_token,
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise ValueError(f"job is not running with a valid lease: {job_id}")
            connection.commit()

    def request_approval(
        self,
        job_id: str,
        *,
        result: dict[str, Any],
        evidence_reference: str,
        worker_id: str,
        lease_token: str,
    ) -> None:
        if not isinstance(evidence_reference, str) or not evidence_reference.strip():
            raise ValueError("evidence_reference must not be empty")
        now = time.time()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE control_plane_tasks SET state='awaiting_approval', "
                "result_json=?, error_text='approval_required', "
                "worker_id=NULL, lease_until=NULL, lease_token=NULL, updated_at=? "
                "WHERE job_id=? AND state='running' AND lease_until>? "
                "AND worker_id=? AND lease_token=?",
                (
                    self._json({**dict(result), "evidence_reference": evidence_reference}),
                    now,
                    job_id,
                    now,
                    worker_id,
                    lease_token,
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise ValueError(f"job is not running with a valid lease: {job_id}")
            connection.commit()

    def approve_pending_completion(
        self, job_id: str, *, execution_grant: dict[str, Any], evidence_reference: str
    ) -> None:
        now = time.time()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT result_json FROM control_plane_tasks "
                "WHERE job_id=? AND state='awaiting_approval'",
                (job_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise ValueError(f"task is not awaiting approval: {job_id}")
            try:
                completed_result = json.loads(row["result_json"] or "{}")
            except (TypeError, json.JSONDecodeError) as exc:
                connection.rollback()
                raise ValueError("pending approval result is invalid") from exc
            if completed_result.get("evidence_reference") != evidence_reference:
                connection.rollback()
                raise ValueError("approval evidence reference does not match pending result")
            approver_id = self._consume_completion_grant(
                connection,
                job_id=job_id,
                evidence_reference=evidence_reference,
                completion_result=completed_result,
                execution_grant=execution_grant,
            )
            completed_result["approver_id"] = approver_id
            checkpoint = {
                "state": "completed",
                "evidence_reference": evidence_reference,
                "approver_id": approver_id,
            }
            cursor = connection.execute(
                "UPDATE control_plane_tasks SET state='completed', "
                "result_json=?, checkpoint_json=?, "
                "error_text=NULL, updated_at=? WHERE job_id=? AND state='awaiting_approval'",
                (self._json(completed_result), self._json(checkpoint), now, job_id),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise ValueError(f"task is not awaiting approval: {job_id}")
            connection.commit()

    @staticmethod
    def _completion_params_hash(
        job_id: str, evidence_reference: str, completion_result: dict[str, Any]
    ) -> str:
        payload = {"job_id": job_id, "result": completion_result}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _consume_completion_grant(
        self,
        connection: sqlite3.Connection,
        *,
        job_id: str,
        evidence_reference: str | None,
        completion_result: dict[str, Any],
        execution_grant: dict[str, Any] | None,
    ) -> str:
        def deny() -> None:
            raise PermissionError(
                "successful completion requires a valid task-bound Core/L3 capability grant "
                "(one-time, signed, and backed by verified evidence)"
            )

        if not isinstance(evidence_reference, str) or not evidence_reference.strip():
            deny()
        if not isinstance(execution_grant, dict) or len(self.grant_secret) < 32:
            deny()
        required = {
            "grant_id",
            "agent_id",
            "capability_id",
            "params_hash",
            "task_id",
            "expires_at",
            "signature",
        }
        if not required.issubset(execution_grant):
            deny()
        unsigned = {key: value for key, value in execution_grant.items() if key != "signature"}
        signature = execution_grant.get("signature")
        if not isinstance(signature, str):
            deny()
        raw = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected_signature = hmac.new(self.grant_secret, raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            deny()
        if (
            unsigned.get("task_id") != job_id
            or unsigned.get("capability_id") != COMPLETION_CAPABILITY_ID
            or not isinstance(unsigned.get("agent_id"), str)
            or not unsigned["agent_id"].strip()
            or unsigned.get("params_hash")
            != self._completion_params_hash(job_id, evidence_reference, completion_result)
            or isinstance(unsigned.get("expires_at"), bool)
            or not isinstance(unsigned.get("expires_at"), int)
            or unsigned["expires_at"] <= int(time.time())
        ):
            deny()
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if not {"grants", "evidence"}.issubset(tables):
            deny()
        grant = connection.execute(
            "SELECT * FROM grants WHERE grant_id=?", (unsigned["grant_id"],)
        ).fetchone()
        if not grant or grant["used"] or grant["expires_at"] <= int(time.time()):
            deny()
        if (
            grant["agent_id"] != unsigned["agent_id"]
            or grant["capability_id"] != COMPLETION_CAPABILITY_ID
            or grant["params_hash"] != unsigned["params_hash"]
            or grant["task_id"] != job_id
            or grant["expires_at"] != unsigned["expires_at"]
        ):
            deny()
        evidence = connection.execute(
            "SELECT 1 FROM evidence WHERE ref=? AND task_id=? "
            "AND verified=1 AND revoked=0 AND quality>0",
            (evidence_reference, job_id),
        ).fetchone()
        if evidence is None:
            deny()
        consumed = connection.execute(
            "UPDATE grants SET used=1 WHERE grant_id=? AND used=0 AND expires_at>? AND task_id=?",
            (unsigned["grant_id"], int(time.time()), job_id),
        )
        if consumed.rowcount != 1:
            deny()
        return unsigned["agent_id"]

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
