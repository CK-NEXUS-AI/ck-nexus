"""Privacy-minimizing append-only journal for observed agent outcomes."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

_OUTCOMES = frozenset({"reported_success", "reported_failure", "blocked", "unknown"})
_REASON_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
_REF_RE = re.compile(r"^[A-Za-z0-9_.:/-]{1,200}$")
_SECRET_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|"
    r"AIza[0-9A-Za-z_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)
_ALLOWED_METRICS = frozenset(
    {
        "duration_ms",
        "input_tokens",
        "output_tokens",
        "retry_count",
        "cost_microusd",
        "test_count",
        "failure_count",
    }
)


class BrainJournal:
    """SQLite append-only observations and unapproved improvement candidates."""

    def __init__(self, database: str | Path) -> None:
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS brain_observations (
                    event_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    task_fingerprint TEXT NOT NULL,
                    outcome TEXT NOT NULL CHECK (
                        outcome IN (
                            'reported_success',
                            'reported_failure',
                            'blocked',
                            'unknown'
                        )
                    ),
                    reason_code TEXT NOT NULL,
                    evidence_refs_json TEXT NOT NULL,
                    metrics_json TEXT NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_brain_observations_created
                ON brain_observations(created_at DESC)
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS brain_improvement_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    candidate_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    evidence_refs_json TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'candidate'
                        CHECK(state IN ('candidate', 'accepted', 'rejected')),
                    decision_actor TEXT,
                    decision_at TEXT
                )
                """
            )
        self.database.chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        return db

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _safe_refs(refs: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        if not isinstance(refs, (tuple, list)) or len(refs) > 20:
            raise ValueError("evidence_refs must contain at most 20 references")
        clean = []
        for ref in refs:
            if not isinstance(ref, str) or not _REF_RE.fullmatch(ref) or _SECRET_RE.search(ref):
                raise ValueError("evidence reference is invalid or secret-shaped")
            clean.append(ref)
        return tuple(clean)

    @staticmethod
    def _safe_metrics(
        metrics: dict[str, int | float] | None,
    ) -> dict[str, int | float]:
        if metrics is None:
            return {}
        if not isinstance(metrics, dict):
            raise ValueError("metrics must be an object")
        clean: dict[str, int | float] = {}
        for key, value in metrics.items():
            if (
                key in _ALLOWED_METRICS
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and 0 <= value <= 10**12
            ):
                clean[key] = value
        return clean

    def record_observation(
        self,
        *,
        task: str,
        outcome: str,
        reason_code: str = "unspecified",
        evidence_refs: tuple[str, ...] | list[str] = (),
        metrics: dict[str, int | float] | None = None,
    ) -> dict[str, object]:
        """Record a bounded observation; never label self-reported data verified."""
        if not isinstance(task, str) or not task.strip() or len(task) > 20_000:
            raise ValueError("task must be non-empty and at most 20000 characters")
        if outcome not in _OUTCOMES:
            raise ValueError("unsupported observation outcome")
        if not isinstance(reason_code, str) or not _REASON_RE.fullmatch(reason_code):
            raise ValueError("reason_code must be a short machine-readable code")

        refs = self._safe_refs(evidence_refs)
        clean_metrics = self._safe_metrics(metrics)
        fingerprint = hashlib.sha256(" ".join(task.split()).encode()).hexdigest()
        event_id = f"brain_evt_{uuid4().hex}"
        created = datetime.now(UTC).isoformat()
        with closing(self._connect()) as db:
            db.execute(
                """
                INSERT INTO brain_observations
                (event_id, created_at, task_fingerprint, outcome, reason_code,
                 evidence_refs_json, metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    created,
                    fingerprint,
                    outcome,
                    reason_code,
                    self._json(refs),
                    self._json(clean_metrics),
                ),
            )
        return {
            "event_id": event_id,
            "task_fingerprint": fingerprint,
            "outcome": outcome,
            "evidence_reference_count": len(refs),
            "raw_task_stored": False,
            "verification_claimed": False,
            "authority": "NONE",
        }

    def propose_improvement(
        self,
        *,
        candidate_type: str,
        title: str,
        rationale: str,
        evidence_refs: tuple[str, ...] | list[str],
    ) -> dict[str, object]:
        """Persist a candidate for review; promotion is intentionally not implemented."""
        if not isinstance(candidate_type, str) or not _REASON_RE.fullmatch(candidate_type):
            raise ValueError("candidate_type must be a short machine-readable code")
        for label, value, limit in (
            ("title", title, 160),
            ("rationale", rationale, 1200),
        ):
            if (
                not isinstance(value, str)
                or not value.strip()
                or len(value) > limit
                or _SECRET_RE.search(value)
            ):
                raise ValueError(f"{label} is invalid or secret-shaped")
        refs = self._safe_refs(evidence_refs)
        if not refs:
            raise ValueError("at least one evidence reference is required")

        candidate_id = f"brain_candidate_{uuid4().hex}"
        created = datetime.now(UTC).isoformat()
        with closing(self._connect()) as db:
            db.execute(
                """
                INSERT INTO brain_improvement_candidates
                (candidate_id, created_at, candidate_type, title, rationale,
                 evidence_refs_json, state)
                VALUES (?, ?, ?, ?, ?, ?, 'candidate')
                """,
                (
                    candidate_id,
                    created,
                    candidate_type,
                    title.strip(),
                    rationale.strip(),
                    self._json(refs),
                ),
            )
        return {
            "candidate_id": candidate_id,
            "state": "candidate",
            "evidence_reference_count": len(refs),
            "owner_approval_required": True,
            "auto_promotion": False,
        }

    def summary(self, *, limit: int = 5) -> dict[str, object]:
        limit = max(1, min(int(limit), 20))
        with closing(self._connect()) as db:
            totals = db.execute(
                """
                SELECT outcome, COUNT(*) AS count
                FROM brain_observations GROUP BY outcome
                """
            ).fetchall()
            candidates = db.execute(
                """
                SELECT COUNT(*) AS count
                FROM brain_improvement_candidates WHERE state = 'candidate'
                """
            ).fetchone()["count"]
            recent = db.execute(
                """
                SELECT event_id, created_at, task_fingerprint, outcome, reason_code
                FROM brain_observations ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return {
            "observation_count": sum(int(row["count"]) for row in totals),
            "outcomes": {str(row["outcome"]): int(row["count"]) for row in totals},
            "pending_improvement_candidates": int(candidates),
            "recent_observations": [dict(row) for row in recent],
            "raw_prompts_or_outputs_stored": False,
            "self_reported_outcomes_are_verified": False,
        }
