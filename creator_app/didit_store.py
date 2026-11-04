from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from creator_app.didit_kyb import (
    DIDIT_ALLOWED_TRANSITIONS,
    DiditVerificationStore,
    validated_event_fields,
)


class PostgresDiditVerificationStore:
    """Shared PostgreSQL store for production/multi-replica KYB webhooks."""

    def __init__(self, database_url: str) -> None:
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("PostgreSQL URL required")
        self.database_url = database_url

    @staticmethod
    def _driver():
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - production dependency
            raise RuntimeError("PostgreSQL Didit store requires psycopg") from exc
        return psycopg, dict_row

    def _connect(self):
        psycopg, dict_row = self._driver()
        return psycopg.connect(self.database_url, row_factory=dict_row)
    def initialize(self) -> None:
        migration = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "postgresql"
            / "003_didit_kyb.sql"
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(migration.read_text(encoding="utf-8"))
            connection.commit()

    def apply_event(self, event: dict[str, Any], *, received_at: int) -> bool:
        event_id, session_id, vendor_data, status = validated_event_fields(event)
        decision = event.get("decision")
        resubmit = event.get("resubmit_info")
        verified = status == "Approved"

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO didit_webhook_events (
                        event_id, session_id, vendor_data, status, received_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                    RETURNING event_id
                    """,
                    (event_id, session_id, vendor_data, status, received_at),
                )
                if cursor.fetchone() is None:
                    connection.commit()
                    return False
                cursor.execute(
                    """
                    SELECT session_id, status
                    FROM didit_business_verifications
                    WHERE vendor_data = %s
                    FOR UPDATE
                    """,
                    (vendor_data,),
                )
                current = cursor.fetchone()
                same_state_repeat = False
                if current and current["session_id"] == session_id:
                    current_status = str(current["status"])
                    if current_status == status:
                        same_state_repeat = True
                    elif status not in DIDIT_ALLOWED_TRANSITIONS[current_status]:
                        raise ValueError(
                            f"invalid Didit state transition: {current_status} -> {status}"
                        )

                if not same_state_repeat:
                    cursor.execute(
                        """
                        INSERT INTO didit_business_verifications (
                            vendor_data, session_id, status, verified,
                            decision_json, resubmit_json, updated_at
                        ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                        ON CONFLICT (vendor_data) DO UPDATE SET
                            session_id=EXCLUDED.session_id,
                            status=EXCLUDED.status,
                            verified=EXCLUDED.verified,
                            decision_json=EXCLUDED.decision_json,
                            resubmit_json=EXCLUDED.resubmit_json,
                            updated_at=EXCLUDED.updated_at
                        """,
                        (
                            vendor_data,
                            session_id,
                            status,
                            verified,
                            json.dumps(decision, ensure_ascii=False)
                            if decision is not None
                            else None,
                            json.dumps(resubmit, ensure_ascii=False)
                            if resubmit is not None
                            else None,
                            received_at,
                        ),
                    )
            connection.commit()
        return True

    def get_business(self, vendor_data: str) -> dict[str, Any] | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM didit_business_verifications WHERE vendor_data = %s",
                (vendor_data,),
            )
            row = cursor.fetchone()
        return dict(row) if row else None
def create_didit_verification_store(
    *,
    database_path: Path,
    database_url: str = "",
    environment: str = "development",
):
    value = database_url.strip()
    if value.startswith(("postgresql://", "postgres://")):
        return PostgresDiditVerificationStore(value)
    if value and not value.startswith("sqlite://"):
        raise ValueError("Unsupported Didit database URL scheme")
    if environment == "production":
        raise RuntimeError(
            "Didit KYB production requires shared PostgreSQL storage; "
            "local SQLite is single-instance only"
        )
    if value.startswith("sqlite:///"):
        database_path = Path(value.removeprefix("sqlite:///"))
    return DiditVerificationStore(database_path)
