from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass(frozen=True, slots=True)
class ClaimResult:
    claimed: bool
    journal_id: str | None
    duplicate_reason: str | None = None


@dataclass(frozen=True, slots=True)
class OutboxItem:
    id: str
    email_journal_id: str
    action_type: str
    destination: str
    payload: dict[str, Any]
    deduplication_key: str
    attempt_count: int


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def build_idempotency_key(*, mailbox: str, provider: str, provider_message_id: str) -> str:
    """Stable hard-dedup key. Subject/body/date are intentionally excluded."""
    canonical = "\x1f".join(
        [mailbox.strip().casefold(), provider.strip().casefold(), provider_message_id.strip()]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class EmailGatewayRepository:
    """SQLite execution adapter for local/runtime tests.

    Production PostgreSQL uses the same schema contract from
    migrations/postgresql/001_email_gateway.sql. This adapter deliberately
    keeps SQL local and dependency-free so P0 concurrency/recovery tests can
    run in the Creator Edition package without requiring a PostgreSQL daemon.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self._init_lock = Lock()

    def initialize(self) -> None:
        with self._init_lock:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            migration = (
                Path(__file__).resolve().parent / "migrations" / "sqlite.sql"
            )
            with self._connect() as connection:
                connection.executescript(migration.read_text(encoding="utf-8"))

    def claim_message(
        self,
        *,
        mailbox: str,
        provider: str,
        provider_message_id: str,
        internet_message_id: str | None = None,
        claimed_by: str,
        lease_seconds: int = 300,
        idempotency_key: str | None = None,
        now: datetime | None = None,
    ) -> ClaimResult:
        if not mailbox.strip() or not provider.strip() or not provider_message_id.strip():
            raise ValueError("mailbox, provider, and provider_message_id are required")
        timestamp = now or utc_now()
        row_id = str(uuid.uuid4())
        dedup_key = idempotency_key or build_idempotency_key(
            mailbox=mailbox,
            provider=provider,
            provider_message_id=provider_message_id,
        )
        locked_until = timestamp + timedelta(seconds=max(1, lease_seconds))

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO email_journal (
                    id, mailbox, provider, provider_message_id, internet_message_id,
                    idempotency_key, status, claimed_by, locked_until, attempt_count,
                    first_seen_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'PROCESSING', ?, ?, 1, ?, ?)
                """,
                (
                    row_id,
                    mailbox.strip(),
                    provider.strip().casefold(),
                    provider_message_id.strip(),
                    internet_message_id,
                    dedup_key,
                    claimed_by,
                    iso(locked_until),
                    iso(timestamp),
                    iso(timestamp),
                ),
            )
            if cursor.rowcount == 1:
                connection.commit()
                return ClaimResult(claimed=True, journal_id=row_id)

            existing = connection.execute(
                """
                SELECT id FROM email_journal
                WHERE mailbox = ? AND provider = ? AND provider_message_id = ?
                """,
                (mailbox.strip(), provider.strip().casefold(), provider_message_id.strip()),
            ).fetchone()
            connection.commit()
            return ClaimResult(
                claimed=False,
                journal_id=str(existing["id"]) if existing else None,
                duplicate_reason="provider_message_already_claimed"
                if existing
                else "idempotency_key_conflict",
            )

    def mark_completed(self, journal_id: str, *, now: datetime | None = None) -> None:
        timestamp = now or utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE email_journal
                SET status='COMPLETED', locked_until=NULL, completed_at=?, updated_at=?
                WHERE id=? AND status='PROCESSING'
                """,
                (iso(timestamp), iso(timestamp), journal_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"journal not PROCESSING: {journal_id}")

    def enqueue_outbox(
        self,
        *,
        email_journal_id: str,
        action_type: str,
        destination: str,
        payload: dict[str, Any],
        deduplication_key: str,
        now: datetime | None = None,
    ) -> tuple[bool, str]:
        timestamp = now or utc_now()
        outbox_id = str(uuid.uuid4())
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO email_outbox (
                    id, email_journal_id, action_type, destination, payload_json,
                    deduplication_key, status, attempt_count, next_attempt_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 0, ?, ?, ?)
                """,
                (
                    outbox_id,
                    email_journal_id,
                    action_type,
                    destination,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    deduplication_key,
                    iso(timestamp),
                    iso(timestamp),
                    iso(timestamp),
                ),
            )
            if cursor.rowcount == 1:
                return True, outbox_id
            row = connection.execute(
                "SELECT id FROM email_outbox WHERE deduplication_key = ?",
                (deduplication_key,),
            ).fetchone()
            if not row:
                raise RuntimeError("outbox deduplication conflict without existing row")
            return False, str(row["id"])

    def claim_outbox_batch(
        self,
        *,
        worker_id: str,
        limit: int = 20,
        lease_seconds: int = 120,
        now: datetime | None = None,
    ) -> list[OutboxItem]:
        timestamp = now or utc_now()
        lease_until = timestamp + timedelta(seconds=max(1, lease_seconds))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT id FROM email_outbox
                WHERE status IN ('PENDING','FAILED_RETRYABLE')
                  AND next_attempt_at <= ?
                  AND (locked_until IS NULL OR locked_until < ?)
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (iso(timestamp), iso(timestamp), max(1, limit)),
            ).fetchall()
            ids = [str(row["id"]) for row in rows]
            if not ids:
                connection.commit()
                return []
            placeholders = ",".join("?" for _ in ids)
            connection.execute(
                f"""
                UPDATE email_outbox
                SET status='SENDING', claimed_by=?, locked_until=?,
                    attempt_count=attempt_count+1, updated_at=?
                WHERE id IN ({placeholders})
                """,
                (worker_id, iso(lease_until), iso(timestamp), *ids),
            )
            claimed = connection.execute(
                f"""
                SELECT id, email_journal_id, action_type, destination, payload_json,
                       deduplication_key, attempt_count
                FROM email_outbox
                WHERE id IN ({placeholders})
                ORDER BY created_at ASC
                """,
                ids,
            ).fetchall()
            connection.commit()
        return [
            OutboxItem(
                id=str(row["id"]),
                email_journal_id=str(row["email_journal_id"]),
                action_type=str(row["action_type"]),
                destination=str(row["destination"]),
                payload=json.loads(row["payload_json"]),
                deduplication_key=str(row["deduplication_key"]),
                attempt_count=int(row["attempt_count"]),
            )
            for row in claimed
        ]

    def mark_outbox_sent(
        self,
        outbox_id: str,
        *,
        provider_message_id: str | None = None,
        now: datetime | None = None,
    ) -> None:
        timestamp = now or utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE email_outbox
                SET status='SENT', provider_message_id=?, sent_at=?, locked_until=NULL,
                    claimed_by=NULL, updated_at=?, last_error=NULL
                WHERE id=?
                """,
                (provider_message_id, iso(timestamp), iso(timestamp), outbox_id),
            )

    def mark_outbox_retry(
        self,
        outbox_id: str,
        *,
        error: str,
        base_delay_seconds: int = 5,
        max_delay_seconds: int = 900,
        now: datetime | None = None,
    ) -> None:
        timestamp = now or utc_now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT attempt_count FROM email_outbox WHERE id=?",
                (outbox_id,),
            ).fetchone()
            if not row:
                raise LookupError(outbox_id)
            attempt = max(1, int(row["attempt_count"]))
            delay = min(max_delay_seconds, base_delay_seconds * (2 ** (attempt - 1)))
            next_attempt = timestamp + timedelta(seconds=delay)
            connection.execute(
                """
                UPDATE email_outbox
                SET status='FAILED_RETRYABLE', next_attempt_at=?, locked_until=NULL,
                    claimed_by=NULL, updated_at=?, last_error=?
                WHERE id=?
                """,
                (iso(next_attempt), iso(timestamp), error[:2000], outbox_id),
            )

    def recover_expired_leases(self, *, now: datetime | None = None) -> dict[str, int]:
        timestamp = now or utc_now()
        now_iso = iso(timestamp)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            journal = connection.execute(
                """
                UPDATE email_journal
                SET status='FAILED_RETRYABLE', claimed_by=NULL, locked_until=NULL,
                    updated_at=?, last_error_code='PROCESSING_LEASE_EXPIRED',
                    last_error_at=?
                WHERE status='PROCESSING' AND locked_until IS NOT NULL AND locked_until < ?
                """,
                (now_iso, now_iso, now_iso),
            ).rowcount
            outbox = connection.execute(
                """
                UPDATE email_outbox
                SET status='FAILED_RETRYABLE', claimed_by=NULL, locked_until=NULL,
                    next_attempt_at=?, updated_at=?, last_error='OUTBOX_LEASE_EXPIRED'
                WHERE status='SENDING' AND locked_until IS NOT NULL AND locked_until < ?
                """,
                (now_iso, now_iso, now_iso),
            ).rowcount
            connection.commit()
        return {"journal": journal, "outbox": outbox}

    def audit(
        self,
        *,
        event_type: str,
        result: str,
        email_journal_id: str | None = None,
        actor_type: str = "system",
        actor_id: str | None = None,
        routing_category: str | None = None,
        action: str | None = None,
        details: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> str:
        audit_id = str(uuid.uuid4())
        timestamp = now or utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO email_audit_logs (
                    id, email_journal_id, event_type, actor_type, actor_id,
                    routing_category, action, result, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id, email_journal_id, event_type, actor_type, actor_id,
                    routing_category, action, result,
                    json.dumps(details or {}, ensure_ascii=False, sort_keys=True),
                    iso(timestamp),
                ),
            )
        return audit_id

    def trace_audit(self, journal_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM email_audit_logs WHERE email_journal_id=? ORDER BY created_at, id",
                (journal_id,),
            ).fetchall()
        output = []
        for row in rows:
            item = dict(row)
            item["details"] = json.loads(item.pop("details_json"))
            output.append(item)
        return output

    def metrics_snapshot(self, *, now: datetime | None = None) -> dict[str, int]:
        timestamp = now or utc_now()
        now_iso = iso(timestamp)
        with self._connect() as connection:
            journal_total = int(connection.execute("SELECT COUNT(*) FROM email_journal").fetchone()[0])
            duplicates = int(connection.execute(
                "SELECT COUNT(*) FROM email_audit_logs WHERE event_type='INGRESS_DUPLICATE'"
            ).fetchone()[0])
            outbox_pending = int(connection.execute(
                "SELECT COUNT(*) FROM email_outbox WHERE status IN ('PENDING','FAILED_RETRYABLE')"
            ).fetchone()[0])
            outbox_sending = int(connection.execute(
                "SELECT COUNT(*) FROM email_outbox WHERE status='SENDING'"
            ).fetchone()[0])
            stale_journal = int(connection.execute(
                "SELECT COUNT(*) FROM email_journal WHERE status='PROCESSING' AND locked_until IS NOT NULL AND locked_until < ?",
                (now_iso,),
            ).fetchone()[0])
        return {
            "journal_total": journal_total,
            "duplicates_total": duplicates,
            "outbox_pending": outbox_pending,
            "outbox_sending": outbox_sending,
            "stale_journal_leases": stale_journal,
        }

    def get_journal(self, journal_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM email_journal WHERE id=?",
                (journal_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_outbox(self, outbox_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM email_outbox WHERE id=?",
                (outbox_id,),
            ).fetchone()
        return dict(row) if row else None

    def count_journal(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM email_journal").fetchone()[0])

    def count_journal_message(
        self, *, mailbox: str, provider: str, provider_message_id: str
    ) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) FROM email_journal
                WHERE mailbox = ? AND provider = ? AND provider_message_id = ?
                """,
                (mailbox.strip(), provider.strip().casefold(), provider_message_id.strip()),
            ).fetchone()
        return int(row[0])

    def count_outbox(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM email_outbox").fetchone()[0])

    def run_outbox_once(
        self,
        *,
        worker_id: str,
        sender: Callable[[OutboxItem], str | None],
        limit: int = 20,
        now: datetime | None = None,
    ) -> dict[str, int]:
        items = self.claim_outbox_batch(worker_id=worker_id, limit=limit, now=now)
        sent = 0
        retry = 0
        for item in items:
            try:
                provider_message_id = sender(item)
            except Exception as exc:  # sender boundary: retain job instead of losing it
                self.mark_outbox_retry(item.id, error=f"{type(exc).__name__}: {exc}", now=now)
                retry += 1
            else:
                self.mark_outbox_sent(
                    item.id,
                    provider_message_id=provider_message_id,
                    now=now,
                )
                sent += 1
        return {"claimed": len(items), "sent": sent, "retry": retry}

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection
