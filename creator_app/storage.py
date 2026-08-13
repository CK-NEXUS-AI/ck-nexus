from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any

from creator_app.schemas import RunResult


class _SQLiteRunStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._write_lock = Lock()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS creator_runs (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    brief_json TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_creator_runs_session_created "
                "ON creator_runs(session_id, created_at DESC)"
            )

    def save(self, run: RunResult) -> None:
        brief = {
            "audience": run.audience,
            "platform": run.platform,
            "tone": run.tone,
            "language": run.language,
        }
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO creator_runs (
                    id, session_id, agent_id, agent_name, prompt, brief_json,
                    content, model, mode, status, duration_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.session_id,
                    run.agent_id,
                    run.agent_name,
                    run.prompt,
                    json.dumps(brief, ensure_ascii=False),
                    run.content,
                    run.model,
                    run.mode,
                    run.status,
                    run.duration_ms,
                    run.created_at.isoformat(),
                ),
            )

    def list(self, *, limit: int, session_id: str | None = None) -> list[RunResult]:
        sql = "SELECT * FROM creator_runs"
        params: list[object] = []
        if session_id:
            sql += " WHERE session_id = ?"
            params.append(session_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._from_row(dict(row)) for row in rows]

    def get(self, run_id: str) -> RunResult | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM creator_runs WHERE id = ?", (run_id,)
            ).fetchone()
        return self._from_row(dict(row)) if row else None

    def delete_session(self, session_id: str) -> int:
        with self._write_lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM creator_runs WHERE session_id = ?", (session_id,)
            )
            return cursor.rowcount

    def ping(self) -> bool:
        try:
            with self._connect() as connection:
                return connection.execute("SELECT 1").fetchone()[0] == 1
        except Exception:
            return False

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _from_row(row: dict[str, Any]) -> RunResult:
        brief = json.loads(row["brief_json"])
        return RunResult(
            id=row["id"],
            session_id=row["session_id"],
            agent_id=row["agent_id"],
            agent_name=row["agent_name"],
            prompt=row["prompt"],
            audience=brief["audience"],
            platform=brief["platform"],
            tone=brief["tone"],
            language=brief["language"],
            content=row["content"],
            model=row["model"],
            mode=row["mode"],
            status=row["status"],
            duration_ms=row["duration_ms"],
            created_at=row["created_at"],
        )


class _PostgresRunStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    @staticmethod
    def _driver():
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL storage requires the `email`/production dependencies"
            ) from exc
        return psycopg, dict_row

    def _connect(self):
        psycopg, dict_row = self._driver()
        return psycopg.connect(self.database_url, autocommit=False, row_factory=dict_row)

    def initialize(self) -> None:
        migration = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "postgresql"
            / "002_creator_runs.sql"
        )
        sql = migration.read_text(encoding="utf-8")
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(sql)
            connection.commit()

    def save(self, run: RunResult) -> None:
        brief = json.dumps(
            {
                "audience": run.audience,
                "platform": run.platform,
                "tone": run.tone,
                "language": run.language,
            },
            ensure_ascii=False,
        )
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO creator_runs (
                    id, session_id, agent_id, agent_name, prompt, brief_json,
                    content, model, mode, status, duration_ms, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    run.id,
                    run.session_id,
                    run.agent_id,
                    run.agent_name,
                    run.prompt,
                    brief,
                    run.content,
                    run.model,
                    run.mode,
                    run.status,
                    run.duration_ms,
                    run.created_at,
                ),
            )
            connection.commit()

    def list(self, *, limit: int, session_id: str | None = None) -> list[RunResult]:
        sql = "SELECT * FROM creator_runs"
        params: list[object] = []
        if session_id:
            sql += " WHERE session_id = %s"
            params.append(session_id)
        sql += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [self._from_row(row) for row in rows]

    def get(self, run_id: str) -> RunResult | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT * FROM creator_runs WHERE id = %s", (run_id,))
            row = cursor.fetchone()
        return self._from_row(row) if row else None

    def delete_session(self, session_id: str) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM creator_runs WHERE session_id = %s", (session_id,))
            count = cursor.rowcount
            connection.commit()
        return count

    def ping(self) -> bool:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() is not None
        except Exception:
            return False

    @staticmethod
    def _from_row(row: dict[str, Any]) -> RunResult:
        brief_raw = row["brief_json"]
        brief = brief_raw if isinstance(brief_raw, dict) else json.loads(brief_raw)
        return RunResult(
            id=row["id"],
            session_id=row["session_id"],
            agent_id=row["agent_id"],
            agent_name=row["agent_name"],
            prompt=row["prompt"],
            audience=brief["audience"],
            platform=brief["platform"],
            tone=brief["tone"],
            language=brief["language"],
            content=row["content"],
            model=row["model"],
            mode=row["mode"],
            status=row["status"],
            duration_ms=row["duration_ms"],
            created_at=row["created_at"],
        )


class RunStore:
    (
        "Creator history store. PostgreSQL is used when database_url is supplied; "
        "SQLite is local/test fallback."
    )

    def __init__(self, database_path: Path, *, database_url: str = "") -> None:
        self._impl = (
            _PostgresRunStore(database_url) if database_url else _SQLiteRunStore(database_path)
        )

    def initialize(self) -> None:
        self._impl.initialize()

    def save(self, run: RunResult) -> None:
        self._impl.save(run)

    def list(self, *, limit: int, session_id: str | None = None) -> list[RunResult]:
        return self._impl.list(limit=limit, session_id=session_id)

    def get(self, run_id: str) -> RunResult | None:
        return self._impl.get(run_id)

    def delete_session(self, session_id: str) -> int:
        return self._impl.delete_session(session_id)

    def ping(self) -> bool:
        return self._impl.ping()
