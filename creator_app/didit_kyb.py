from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import httpx

DIDIT_API_BASE = "https://verification.didit.me"
DIDIT_KYB_WORKFLOW_ID = "d483655c-0adf-4c47-9d5f-b370d16aece8"
DIDIT_STATUSES = {
    "Not Started",
    "In Progress",
    "Awaiting User",
    "In Review",
    "Approved",
    "Declined",
    "Resubmitted",
    "Abandoned",
    "Expired",
    "Kyc Expired",
}

# Rules apply within one Didit session. A new session_id starts a new lifecycle.
# Same-state repeats are event-log no-ops because provider retries may use a new
# event_id; the business verification row is not overwritten.
DIDIT_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "Not Started": frozenset({
        "In Progress", "Awaiting User", "In Review", "Approved", "Declined",
        "Resubmitted", "Abandoned", "Expired",
    }),
    "In Progress": frozenset({
        "Awaiting User", "In Review", "Approved", "Declined",
        "Resubmitted", "Abandoned", "Expired",
    }),
    "Awaiting User": frozenset({
        "In Progress", "In Review", "Approved", "Declined",
        "Resubmitted", "Abandoned", "Expired",
    }),
    "In Review": frozenset({
        "Approved", "Declined", "Resubmitted", "Abandoned", "Expired",
    }),
    "Resubmitted": frozenset({
        "Not Started", "In Progress", "Awaiting User", "In Review",
        "Approved", "Declined", "Abandoned", "Expired",
    }),
    # Approved can become Kyc Expired only when Didit's reverification policy
    # expires the previously verified session.
    "Approved": frozenset({"Kyc Expired"}),
    # Declined/Abandoned can reopen only through an explicit Resubmitted event.
    "Declined": frozenset({"Resubmitted"}),
    "Abandoned": frozenset({"Resubmitted"}),
    # Expired and Kyc Expired require a new session_id.
    "Expired": frozenset(),
    "Kyc Expired": frozenset(),
}


class DiditConfigurationError(RuntimeError):
    pass


class DiditUpstreamError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DiditConfig:
    api_key: str
    webhook_secret: str
    workflow_id: str = DIDIT_KYB_WORKFLOW_ID
    api_base: str = DIDIT_API_BASE

    @classmethod
    def from_env(cls) -> DiditConfig:
        return cls(
            api_key=os.getenv("DIDIT_API_KEY", "").strip(),
            webhook_secret=os.getenv("DIDIT_WEBHOOK_SECRET", "").strip(),
        )

    @property
    def session_ready(self) -> bool:
        return bool(self.api_key)

    @property
    def webhook_ready(self) -> bool:
        return bool(self.webhook_secret)
class DiditClient:
    def __init__(self, config: DiditConfig, *, timeout_seconds: float = 10.0) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds

    async def create_kyb_session(self, *, vendor_data: str) -> dict[str, str]:
        if not self.config.api_key:
            raise DiditConfigurationError("DIDIT_API_KEY is not configured")
        payload = {
            "workflow_id": self.config.workflow_id,
            "vendor_data": vendor_data,
            "vendor_business_id": vendor_data,
        }
        headers = {"x-api-key": self.config.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.config.api_base}/v3/session/", headers=headers, json=payload
            )
        if response.status_code != 201:
            raise DiditUpstreamError(f"Didit session creation failed ({response.status_code})")
        data = response.json()
        required = ("session_id", "session_token")
        if any(not isinstance(data.get(key), str) or not data[key] for key in required):
            raise DiditUpstreamError("Didit session response is incomplete")
        return {"session_id": data["session_id"], "session_token": data["session_token"]}
def _shorten_floats(value: Any) -> Any:
    if isinstance(value, list):
        return [_shorten_floats(item) for item in value]
    if isinstance(value, dict):
        return {key: _shorten_floats(item) for key, item in value.items()}
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def canonicalize_webhook(payload: dict[str, Any]) -> bytes:
    normalized = _shorten_floats(payload)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def verify_webhook_signature(
    *,
    payload: dict[str, Any],
    signature: str,
    secret: str,
) -> bool:
    if not signature or not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), canonicalize_webhook(payload), hashlib.sha256)
    return hmac.compare_digest(expected.hexdigest(), signature)
class DiditVerificationStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._lock = Lock()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS didit_webhook_events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    vendor_data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    received_at INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS didit_business_verifications (
                    vendor_data TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 0,
                    decision_json TEXT,
                    resubmit_json TEXT,
                    updated_at INTEGER NOT NULL
                )
                """
            )
    def apply_event(self, event: dict[str, Any], *, received_at: int) -> bool:
        event_id = str(event.get("event_id") or "")
        session_id = str(event.get("session_id") or "")
        vendor_data = str(event.get("vendor_data") or event.get("vendor_business_id") or "")
        status = str(event.get("status") or "")
        if not event_id or not session_id or not vendor_data or status not in DIDIT_STATUSES:
            raise ValueError("invalid Didit webhook envelope")

        decision = event.get("decision")
        resubmit = event.get("resubmit_info")
        verified = 1 if status == "Approved" else 0
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM didit_webhook_events WHERE event_id = ?", (event_id,)
            ).fetchone()
            if existing:
                return False

            current = conn.execute(
                "SELECT session_id, status FROM didit_business_verifications WHERE vendor_data = ?",
                (vendor_data,),
            ).fetchone()
            same_state_repeat = False
            if current and current["session_id"] == session_id:
                current_status = str(current["status"])
                if current_status == status:
                    same_state_repeat = True
                elif status not in DIDIT_ALLOWED_TRANSITIONS[current_status]:
                    raise ValueError(
                        f"invalid Didit state transition: {current_status} -> {status}"
                    )

            conn.execute(
                "INSERT INTO didit_webhook_events VALUES (?, ?, ?, ?, ?)",
                (event_id, session_id, vendor_data, status, received_at),
            )
            if same_state_repeat:
                return True

            conn.execute(
                """
                INSERT INTO didit_business_verifications
                    (
                        vendor_data, session_id, status, verified,
                        decision_json, resubmit_json, updated_at
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vendor_data) DO UPDATE SET
                    session_id=excluded.session_id,
                    status=excluded.status,
                    verified=excluded.verified,
                    decision_json=excluded.decision_json,
                    resubmit_json=excluded.resubmit_json,
                    updated_at=excluded.updated_at
                """,
                (
                    vendor_data,
                    session_id,
                    status,
                    verified,
                    json.dumps(decision, ensure_ascii=False) if decision is not None else None,
                    json.dumps(resubmit, ensure_ascii=False) if resubmit is not None else None,
                    received_at,
                ),
            )
        return True

    def get_business(self, vendor_data: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM didit_business_verifications WHERE vendor_data = ?",
                (vendor_data,),
            ).fetchone()
        return dict(row) if row else None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn
