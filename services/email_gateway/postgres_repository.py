from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from services.email_gateway.repository import ClaimResult, OutboxItem, build_idempotency_key


def utc_now() -> datetime:
    return datetime.now(UTC)


class PostgresEmailGatewayRepository:
    """Production repository using PostgreSQL atomic constraints and SKIP LOCKED."""

    def __init__(self, database_url: str) -> None:
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("PostgreSQL URL required")
        self.database_url = database_url

    @staticmethod
    def _driver():
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - depends on production extra
            raise RuntimeError(
                "PostgreSQL Email Gateway requires the 'email' extra: pip install -e '.[email]'"
            ) from exc
        return psycopg, dict_row

    def _connect(self):
        psycopg, dict_row = self._driver()
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def initialize(self) -> None:
        migration = Path(__file__).resolve().parent / "migrations" / "postgresql.sql"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(migration.read_text(encoding="utf-8"))
            connection.commit()

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
        dedup_key = idempotency_key or build_idempotency_key(
            mailbox=mailbox,
            provider=provider,
            provider_message_id=provider_message_id,
        )
        locked_until = timestamp + timedelta(seconds=max(1, lease_seconds))
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO email_journal (
                        mailbox, provider, provider_message_id, internet_message_id,
                        idempotency_key, status, claimed_by, locked_until, attempt_count,
                        first_seen_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, 'PROCESSING', %s, %s, 1, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """,
                    (
                        mailbox.strip(),
                        provider.strip().casefold(),
                        provider_message_id.strip(),
                        internet_message_id,
                        dedup_key,
                        claimed_by,
                        locked_until,
                        timestamp,
                        timestamp,
                    ),
                )
                row = cursor.fetchone()
                if row:
                    connection.commit()
                    return ClaimResult(True, str(row["id"]))
                cursor.execute(
                    """
                    SELECT id FROM email_journal
                    WHERE mailbox=%s AND provider=%s AND provider_message_id=%s
                    """,
                    (mailbox.strip(), provider.strip().casefold(), provider_message_id.strip()),
                )
                existing = cursor.fetchone()
            connection.commit()
        return ClaimResult(
            False,
            str(existing["id"]) if existing else None,
            "provider_message_already_claimed" if existing else "idempotency_key_conflict",
        )

    def mark_completed(self, journal_id: str, *, now: datetime | None = None) -> None:
        timestamp = now or utc_now()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE email_journal
                    SET status='COMPLETED', locked_until=NULL, completed_at=%s, updated_at=%s
                    WHERE id=%s AND status='PROCESSING'
                    """,
                    (timestamp, timestamp, journal_id),
                )
                if cursor.rowcount != 1:
                    raise LookupError(f"journal not PROCESSING: {journal_id}")
            connection.commit()

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
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO email_outbox (
                        email_journal_id, action_type, destination, payload, deduplication_key,
                        status, attempt_count, next_attempt_at, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s::jsonb, %s, 'PENDING', 0, %s, %s, %s)
                    ON CONFLICT (deduplication_key) DO NOTHING
                    RETURNING id
                    """,
                    (
                        email_journal_id,
                        action_type,
                        destination,
                        json.dumps(payload, ensure_ascii=False, sort_keys=True),
                        deduplication_key,
                        timestamp,
                        timestamp,
                        timestamp,
                    ),
                )
                row = cursor.fetchone()
                if row:
                    connection.commit()
                    return True, str(row["id"])
                cursor.execute(
                    "SELECT id FROM email_outbox WHERE deduplication_key=%s",
                    (deduplication_key,),
                )
                existing = cursor.fetchone()
            connection.commit()
        if not existing:
            raise RuntimeError("outbox deduplication conflict without existing row")
        return False, str(existing["id"])

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
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    WITH candidates AS (
                        SELECT id
                        FROM email_outbox
                        WHERE status IN ('PENDING','FAILED_RETRYABLE')
                          AND next_attempt_at <= %s
                          AND (locked_until IS NULL OR locked_until < %s)
                        ORDER BY created_at
                        FOR UPDATE SKIP LOCKED
                        LIMIT %s
                    )
                    UPDATE email_outbox AS o
                    SET status='SENDING', claimed_by=%s, locked_until=%s,
                        attempt_count=o.attempt_count+1, updated_at=%s
                    FROM candidates
                    WHERE o.id=candidates.id
                    RETURNING o.id, o.email_journal_id, o.action_type, o.destination,
                              o.payload, o.deduplication_key, o.attempt_count
                    """,
                    (timestamp, timestamp, max(1, limit), worker_id, lease_until, timestamp),
                )
                rows = cursor.fetchall()
            connection.commit()
        return [
            OutboxItem(
                id=str(row["id"]),
                email_journal_id=str(row["email_journal_id"]),
                action_type=str(row["action_type"]),
                destination=str(row["destination"]),
                payload=dict(row["payload"]),
                deduplication_key=str(row["deduplication_key"]),
                attempt_count=int(row["attempt_count"]),
            )
            for row in rows
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
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE email_outbox
                    SET status='SENT', provider_message_id=%s, sent_at=%s,
                        locked_until=NULL, claimed_by=NULL, updated_at=%s, last_error=NULL
                    WHERE id=%s
                    """,
                    (provider_message_id, timestamp, timestamp, outbox_id),
                )
            connection.commit()

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
            with connection.cursor() as cursor:
                cursor.execute("SELECT attempt_count FROM email_outbox WHERE id=%s", (outbox_id,))
                row = cursor.fetchone()
                if not row:
                    raise LookupError(outbox_id)
                attempt = max(1, int(row["attempt_count"]))
                delay = min(max_delay_seconds, base_delay_seconds * (2 ** (attempt - 1)))
                next_attempt = timestamp + timedelta(seconds=delay)
                cursor.execute(
                    """
                    UPDATE email_outbox
                    SET status='FAILED_RETRYABLE', next_attempt_at=%s, locked_until=NULL,
                        claimed_by=NULL, updated_at=%s, last_error=%s
                    WHERE id=%s
                    """,
                    (next_attempt, timestamp, error[:2000], outbox_id),
                )
            connection.commit()

    def recover_expired_leases(self, *, now: datetime | None = None) -> dict[str, int]:
        timestamp = now or utc_now()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE email_journal
                    SET status='FAILED_RETRYABLE', claimed_by=NULL, locked_until=NULL,
                        updated_at=%s, last_error_code='PROCESSING_LEASE_EXPIRED', last_error_at=%s
                    WHERE status='PROCESSING' AND locked_until IS NOT NULL AND locked_until < %s
                    """,
                    (timestamp, timestamp, timestamp),
                )
                journal = cursor.rowcount
                cursor.execute(
                    """
                    UPDATE email_outbox
                    SET status='FAILED_RETRYABLE', claimed_by=NULL, locked_until=NULL,
                        next_attempt_at=%s, updated_at=%s, last_error='OUTBOX_LEASE_EXPIRED'
                    WHERE status='SENDING' AND locked_until IS NOT NULL AND locked_until < %s
                    """,
                    (timestamp, timestamp, timestamp),
                )
                outbox = cursor.rowcount
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
        timestamp = now or utc_now()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO email_audit_logs (
                        email_journal_id, event_type, actor_type, actor_id,
                        routing_category, action, result, details, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    RETURNING id
                    """,
                    (
                        email_journal_id,
                        event_type,
                        actor_type,
                        actor_id,
                        routing_category,
                        action,
                        result,
                        json.dumps(details or {}, ensure_ascii=False, sort_keys=True),
                        timestamp,
                    ),
                )
                row = cursor.fetchone()
            connection.commit()
        return str(row["id"])

    def trace_audit(self, journal_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM email_audit_logs WHERE email_journal_id=%s ORDER BY created_at, id",
                (journal_id,),
            )
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def metrics_snapshot(self, *, now: datetime | None = None) -> dict[str, int]:
        timestamp = now or utc_now()
        with self._connect() as connection, connection.cursor() as cursor:
            queries = {
                "journal_total": "SELECT COUNT(*) AS n FROM email_journal",
                "duplicates_total": "SELECT COUNT(*) AS n FROM email_audit_logs "
                "WHERE event_type='INGRESS_DUPLICATE'",
                "outbox_pending": "SELECT COUNT(*) AS n FROM email_outbox "
                "WHERE status IN ('PENDING','FAILED_RETRYABLE')",
                "outbox_sending": "SELECT COUNT(*) AS n FROM email_outbox WHERE status='SENDING'",
            }
            output = {}
            for key, query in queries.items():
                cursor.execute(query)
                output[key] = int(cursor.fetchone()["n"])
            cursor.execute(
                "SELECT COUNT(*) AS n FROM email_journal WHERE status='PROCESSING' AND "
                "locked_until IS NOT NULL AND locked_until < %s",
                (timestamp,),
            )
            output["stale_journal_leases"] = int(cursor.fetchone()["n"])
        return output

    def count_journal(self) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS n FROM email_journal")
            row = cursor.fetchone()
        return int(row["n"])

    def count_journal_message(
        self, *, mailbox: str, provider: str, provider_message_id: str
    ) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                    SELECT COUNT(*) AS n FROM email_journal
                    WHERE mailbox=%s AND provider=%s AND provider_message_id=%s
                    """,
                (mailbox.strip(), provider.strip().casefold(), provider_message_id.strip()),
            )
            row = cursor.fetchone()
        return int(row["n"])

    def run_outbox_once(
        self,
        *,
        worker_id: str,
        sender: Callable[[OutboxItem], str | None],
        limit: int = 20,
        now: datetime | None = None,
    ) -> dict[str, int]:
        items = self.claim_outbox_batch(worker_id=worker_id, limit=limit, now=now)
        sent = retry = 0
        for item in items:
            try:
                provider_message_id = sender(item)
            except Exception as exc:
                self.mark_outbox_retry(item.id, error=f"{type(exc).__name__}: {exc}", now=now)
                self.audit(
                    email_journal_id=item.email_journal_id,
                    event_type="OUTBOX_RETRY",
                    action=item.action_type,
                    result="RETRY",
                    details={"outbox_id": item.id, "error_type": type(exc).__name__},
                    now=now,
                )
                retry += 1
            else:
                self.mark_outbox_sent(item.id, provider_message_id=provider_message_id, now=now)
                self.audit(
                    email_journal_id=item.email_journal_id,
                    event_type="OUTBOX_SENT",
                    action=item.action_type,
                    result="PASS",
                    details={"outbox_id": item.id, "provider_message_id": provider_message_id},
                    now=now,
                )
                sent += 1
        return {"claimed": len(items), "sent": sent, "retry": retry}
