"""Public beta feedback intake with privacy-minimizing storage and review-gated triage."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SECRET_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{16,}|"
    r"AIza[0-9A-Za-z_-]{16,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\b(password|passwd|api[_ -]?key|access[_ -]?token)\s*[:=]\s*\S+)"
)


class PublicFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: str = Field(min_length=1, max_length=16)
    title: str = Field(min_length=4, max_length=120)
    message: str = Field(min_length=20, max_length=3000)
    rating: int | None = Field(default=None, ge=1, le=5)
    steps: str = Field(default="", max_length=1500)
    expected: str = Field(default="", max_length=1000)
    consent: bool
    website: str = Field(default="", max_length=120)  # honeypot; must remain empty

    @field_validator("kind")
    @classmethod
    def valid_kind(cls, value: str) -> str:
        if value not in {"bug", "idea", "review", "other"}:
            raise ValueError("unsupported feedback kind")
        return value

    @field_validator("title", "message", "steps", "expected")
    @classmethod
    def reject_secrets(cls, value: str) -> str:
        if _SECRET_RE.search(value):
            raise ValueError("Do not include passwords, API keys, or access tokens")
        return value


class PublicFeedbackStore:
    """Store public reports without IP addresses, email addresses, or credentials."""

    def __init__(self, database: str | Path) -> None:
        self.database = Path(database)
        self._lock = Lock()

    def initialize(self) -> None:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                """CREATE TABLE IF NOT EXISTS public_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    rating INTEGER,
                    steps TEXT NOT NULL,
                    expected TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    triage_state TEXT NOT NULL DEFAULT 'new',
                    triage_json TEXT,
                    reviewed_at TEXT
                )"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_public_feedback_created "
                "ON public_feedback(created_at DESC)"
            )
            cutoff = (datetime.now(UTC) - timedelta(days=180)).isoformat()
            db.execute("DELETE FROM public_feedback WHERE created_at < ?", (cutoff,))
        with suppress(OSError):
            self.database.chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def submit(self, payload: PublicFeedbackRequest) -> dict[str, str | bool]:
        if not payload.consent:
            raise ValueError("consent is required")
        if payload.website:
            # Bot trap: do not retain the submitted content.
            return {"accepted": True, "feedback_id": "", "message": "Thank you."}
        normalized = " ".join(payload.message.casefold().split())
        fingerprint = hashlib.sha256(f"{payload.kind}:{normalized}".encode()).hexdigest()
        feedback_id = f"fb_{uuid4().hex}"
        created = datetime.now(UTC).isoformat()
        with self._lock, self._connect() as db:
            duplicate = db.execute(
                "SELECT feedback_id FROM public_feedback WHERE fingerprint = ? "
                "AND created_at >= ? ORDER BY created_at DESC LIMIT 1",
                (fingerprint, (datetime.now(UTC) - timedelta(days=14)).isoformat()),
            ).fetchone()
            if duplicate:
                return {
                    "accepted": True,
                    "feedback_id": str(duplicate["feedback_id"]),
                    "message": "A similar report was already received.",
                }
            db.execute(
                """INSERT INTO public_feedback
                (feedback_id, created_at, kind, title, message, rating, steps,
                 expected, fingerprint, triage_state)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (
                    feedback_id,
                    created,
                    payload.kind,
                    payload.title,
                    payload.message,
                    payload.rating,
                    payload.steps,
                    payload.expected,
                    fingerprint,
                ),
            )
        return {"accepted": True, "feedback_id": feedback_id, "message": "Thank you."}

    def list_reports(self, *, limit: int = 50) -> list[dict[str, object]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT feedback_id, created_at, kind, title, message, rating, steps, "
                "expected, triage_state, triage_json, reviewed_at FROM public_feedback "
                "ORDER BY created_at DESC LIMIT ?",
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def triage(self, feedback_id: str) -> dict[str, object] | None:
        with self._lock, self._connect() as db:
            row = db.execute(
                "SELECT kind, title, message, steps, expected FROM public_feedback "
                "WHERE feedback_id = ?",
                (feedback_id,),
            ).fetchone()
            if row is None:
                return None
            text = " ".join(
                str(row[key] or "") for key in ("title", "message", "steps", "expected")
            ).casefold()
            security_terms = (
                "login",
                "password",
                "token",
                "permission",
                "unauthorized",
                "ข้อมูลคนอื่น",
                "รั่ว",
                "security",
                "สิทธิ์",
            )
            outage_terms = (
                "crash",
                "down",
                "unavailable",
                "error 500",
                "ใช้งานไม่ได้",
                "ล่ม",
                "ค้าง",
            )
            if any(term in text for term in security_terms):
                priority, category = "high", "security_or_access"
            elif any(term in text for term in outage_terms):
                priority, category = "high", "availability_or_failure"
            elif row["kind"] == "bug":
                priority, category = "normal", "possible_bug"
            elif row["kind"] == "idea":
                priority, category = "low", "feature_request"
            else:
                priority, category = "normal", "user_experience"
            result = {
                "category": category,
                "priority": priority,
                "assessment": "needs_reproduction",
                "verified": False,
                "reason": (
                    "A user report is a lead, not proof. Reproduce against the current "
                    "build and inspect logs/tests before confirming."
                ),
                "next_steps": [
                    "Reproduce the reported behavior in an isolated test account.",
                    (
                        "Check current application logs and relevant code path without "
                        "exposing other users' data."
                    ),
                    "Create a regression test if the issue is reproducible.",
                    "Propose a minimal fix; run tests and security checks before review.",
                ],
                "external_content_is_untrusted": True,
                "automatic_code_changes": False,
            }
            db.execute(
                "UPDATE public_feedback SET triage_state = 'needs_reproduction', "
                "triage_json = ?, reviewed_at = ? WHERE feedback_id = ?",
                (
                    json.dumps(result, ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                    feedback_id,
                ),
            )
            return {"feedback_id": feedback_id, **result}
