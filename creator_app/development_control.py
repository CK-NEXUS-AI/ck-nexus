"""Collaborative development control plane for CK-NEXUS.

This module owns development-task workflow state and AI competency records only.
It does not own Q10/Q11/Q12/Production authority.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class DevelopmentState(StrEnum):
    RECEIVED = "RECEIVED"
    PLANNED = "PLANNED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    MEASURED = "MEASURED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    COMPLETED = "COMPLETED"


class CompetencyLevel(StrEnum):
    PRO_LEVEL = "PRO_LEVEL"
    OBSERVER = "OBSERVER"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


_ALLOWED_TRANSITIONS: dict[DevelopmentState, frozenset[DevelopmentState]] = {
    DevelopmentState.RECEIVED: frozenset(
        {DevelopmentState.PLANNED, DevelopmentState.BLOCKED}
    ),
    DevelopmentState.PLANNED: frozenset(
        {DevelopmentState.QUEUED, DevelopmentState.BLOCKED}
    ),
    DevelopmentState.QUEUED: frozenset(
        {DevelopmentState.RUNNING, DevelopmentState.BLOCKED}
    ),
    DevelopmentState.RUNNING: frozenset(
        {DevelopmentState.MEASURED, DevelopmentState.BLOCKED}
    ),
    DevelopmentState.BLOCKED: frozenset(
        {
            DevelopmentState.PLANNED,
            DevelopmentState.QUEUED,
            DevelopmentState.RUNNING,
        }
    ),
    DevelopmentState.MEASURED: frozenset(
        {DevelopmentState.REVIEW_REQUIRED, DevelopmentState.BLOCKED}
    ),
    DevelopmentState.REVIEW_REQUIRED: frozenset(
        {
            DevelopmentState.RUNNING,
            DevelopmentState.COMPLETED,
            DevelopmentState.BLOCKED,
        }
    ),
    DevelopmentState.COMPLETED: frozenset(),
}


COMPETENCY_CRITERIA: dict[str, tuple[str, ...]] = {
    "level_1": (
        "unified_operations_contract",
        "central_controller_structure",
        "workflow_states",
        "authority_prohibitions",
        "live_status_reading",
        "role_boundary",
    ),
    "level_2": (
        "git_pr_branch_merge",
        "development_vs_production",
        "ci_cd",
        "secure_coding",
        "sast_dependency_secret_scan",
        "evidence_hash_signature_history",
        "root_cause_and_durable_fix",
    ),
    "level_3": (
        "assigned_work_only",
        "report_results",
        "report_blockers",
        "accept_review",
        "follow_sequence",
        "respect_authority_boundary",
    ),
    "level_4": (
        "openssf_scorecard",
        "owasp_top10",
        "secret_management",
        "least_privilege",
        "data_classification",
    ),
}


@dataclass(frozen=True, slots=True)
class CompetencyAssessment:
    agent_id: str
    display_name: str
    score: float
    level: CompetencyLevel
    level_1_pass: bool
    level_2_pass: bool
    level_3_pass: bool
    level_4_ratio: float
    human_confirmed: bool
    write_allowed: bool
    permissions: tuple[str, ...]
    gaps: tuple[str, ...]
    assessed_at: str

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["level"] = self.level.value
        result["permissions"] = list(self.permissions)
        result["gaps"] = list(self.gaps)
        return result


def evaluate_competency(
    *,
    agent_id: str,
    display_name: str,
    answers: dict[str, bool],
    human_confirmed: bool = False,
) -> CompetencyAssessment:
    """Evaluate one AI against the owner-defined CK-NEXUS competency gate."""
    required_ids = tuple(
        criterion
        for level in ("level_1", "level_2", "level_3", "level_4")
        for criterion in COMPETENCY_CRITERIA[level]
    )
    missing = [criterion for criterion in required_ids if criterion not in answers]
    if missing:
        raise ValueError(f"missing competency criteria: {', '.join(missing)}")

    passed_count = sum(bool(answers[criterion]) for criterion in required_ids)
    score = round((passed_count / len(required_ids)) * 100.0, 2)

    level_1_pass = all(answers[item] for item in COMPETENCY_CRITERIA["level_1"])
    level_2_pass = all(answers[item] for item in COMPETENCY_CRITERIA["level_2"])
    level_3_pass = all(answers[item] for item in COMPETENCY_CRITERIA["level_3"])
    l4_items = COMPETENCY_CRITERIA["level_4"]
    level_4_ratio = sum(bool(answers[item]) for item in l4_items) / len(l4_items)

    strict_pro = (
        score >= 85.0
        and level_1_pass
        and level_2_pass
        and level_3_pass
        and level_4_ratio >= 0.80
    )
    if strict_pro:
        level = CompetencyLevel.PRO_LEVEL
    elif score >= 70.0:
        level = CompetencyLevel.OBSERVER
    else:
        level = CompetencyLevel.NOT_ELIGIBLE

    write_allowed = level is CompetencyLevel.PRO_LEVEL and human_confirmed
    if write_allowed:
        permissions = (
            "read_status",
            "comment",
            "claim_assigned_task",
            "write_development_branch",
            "run_tests",
            "open_draft_pr",
            "propose_change",
        )
    elif level is CompetencyLevel.NOT_ELIGIBLE:
        permissions = ("read_training_material",)
    else:
        permissions = ("read_status", "comment", "propose_non_mutating_change")

    gaps = tuple(criterion for criterion in required_ids if not answers[criterion])
    return CompetencyAssessment(
        agent_id=agent_id.strip(),
        display_name=display_name.strip(),
        score=score,
        level=level,
        level_1_pass=level_1_pass,
        level_2_pass=level_2_pass,
        level_3_pass=level_3_pass,
        level_4_ratio=round(level_4_ratio, 4),
        human_confirmed=human_confirmed,
        write_allowed=write_allowed,
        permissions=permissions,
        gaps=gaps,
        assessed_at=datetime.now(UTC).isoformat(),
    )


class DevelopmentStatusStore:
    """SQLite SSOT for live development state and append-only history."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    state TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    progress INTEGER,
                    current_step TEXT,
                    eta TEXT,
                    blocker TEXT,
                    commit_hash TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS competency (
                    agent_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    assessed_at TEXT NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    observed_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )

    def _record_event(
        self,
        db: sqlite3.Connection,
        *,
        event_type: str,
        actor: str,
        payload: dict[str, Any],
    ) -> None:
        db.execute(
            """
            INSERT INTO events(event_id, observed_at, event_type, actor, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                datetime.now(UTC).isoformat(),
                event_type,
                actor,
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
            ),
        )

    @staticmethod
    def _validate_progress(progress: int | None) -> None:
        if progress is not None and not 0 <= progress <= 100:
            raise ValueError("progress must be between 0 and 100 or omitted")

    def create_task(
        self,
        *,
        task_id: str,
        title: str,
        owner: str,
        priority: str = "P2",
        actor: str,
        current_step: str | None = None,
    ) -> dict[str, Any]:
        if priority not in {"P0", "P1", "P2", "P3"}:
            raise ValueError("priority must be P0, P1, P2, or P3")
        now = datetime.now(UTC).isoformat()
        with self._lock, self._connect() as db:
            db.execute(
                """
                INSERT INTO tasks(
                    task_id, title, owner, state, priority, progress,
                    current_step, eta, blocker, commit_hash, updated_at
                )
                VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, NULL, NULL, ?)
                """,
                (
                    task_id.strip(),
                    title.strip(),
                    owner.strip(),
                    DevelopmentState.RECEIVED.value,
                    priority,
                    current_step,
                    now,
                ),
            )
            self._record_event(
                db,
                event_type="TASK_CREATED",
                actor=actor,
                payload={
                    "task_id": task_id,
                    "state": DevelopmentState.RECEIVED.value,
                    "priority": priority,
                },
            )
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            raise KeyError(task_id)
        return dict(row)

    def transition_task(
        self,
        *,
        task_id: str,
        to_state: DevelopmentState | str,
        actor: str,
        progress: int | None = None,
        current_step: str | None = None,
        eta: str | None = None,
        blocker: str | None = None,
        commit_hash: str | None = None,
        human_reviewed: bool = False,
        merged: bool = False,
    ) -> dict[str, Any]:
        self._validate_progress(progress)
        target = DevelopmentState(to_state)
        with self._lock, self._connect() as db:
            row = db.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            current = DevelopmentState(row["state"])
            if target not in _ALLOWED_TRANSITIONS[current]:
                raise ValueError(
                    f"invalid development transition: {current.value} -> {target.value}"
                )
            if target is DevelopmentState.COMPLETED and not (
                human_reviewed and merged
            ):
                raise PermissionError(
                    "COMPLETED requires human review and recorded merge"
                )
            if target is DevelopmentState.BLOCKED and not (blocker or "").strip():
                raise ValueError("BLOCKED requires a blocker reason")

            now = datetime.now(UTC).isoformat()
            values = {
                "progress": progress if progress is not None else row["progress"],
                "current_step": (
                    current_step if current_step is not None else row["current_step"]
                ),
                "eta": eta if eta is not None else row["eta"],
                "blocker": blocker if target is DevelopmentState.BLOCKED else None,
                "commit_hash": (
                    commit_hash if commit_hash is not None else row["commit_hash"]
                ),
            }
            db.execute(
                """
                UPDATE tasks
                SET state = ?, progress = ?, current_step = ?, eta = ?,
                    blocker = ?, commit_hash = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (
                    target.value,
                    values["progress"],
                    values["current_step"],
                    values["eta"],
                    values["blocker"],
                    values["commit_hash"],
                    now,
                    task_id,
                ),
            )
            self._record_event(
                db,
                event_type="TASK_TRANSITION",
                actor=actor,
                payload={
                    "task_id": task_id,
                    "from_state": current.value,
                    "to_state": target.value,
                    "progress": values["progress"],
                    "current_step": values["current_step"],
                    "eta": values["eta"],
                    "blocker": values["blocker"],
                    "commit_hash": values["commit_hash"],
                    "human_reviewed": human_reviewed,
                    "merged": merged,
                },
            )
        return self.get_task(task_id)

    def save_competency(
        self,
        assessment: CompetencyAssessment,
        *,
        actor: str,
    ) -> dict[str, Any]:
        payload = assessment.as_dict()
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self._lock, self._connect() as db:
            db.execute(
                """
                INSERT INTO competency(agent_id, payload_json, assessed_at)
                VALUES (?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    assessed_at = excluded.assessed_at
                """,
                (assessment.agent_id, encoded, assessment.assessed_at),
            )
            self._record_event(
                db,
                event_type="COMPETENCY_ASSESSED",
                actor=actor,
                payload={
                    "agent_id": assessment.agent_id,
                    "score": assessment.score,
                    "level": assessment.level.value,
                    "human_confirmed": assessment.human_confirmed,
                    "write_allowed": assessment.write_allowed,
                },
            )
        return payload

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        bounded = max(1, min(limit, 500))
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT event_id, observed_at, event_type, actor, payload_json
                FROM events
                ORDER BY observed_at DESC
                LIMIT ?
                """,
                (bounded,),
            ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "observed_at": row["observed_at"],
                "event_type": row["event_type"],
                "actor": row["actor"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def snapshot(self) -> dict[str, Any]:
        with self._connect() as db:
            task_rows = db.execute(
                "SELECT * FROM tasks ORDER BY priority, updated_at DESC"
            ).fetchall()
            competency_rows = db.execute(
                "SELECT payload_json FROM competency ORDER BY assessed_at DESC"
            ).fetchall()

        tasks = [dict(row) for row in task_rows]
        assessments = [json.loads(row["payload_json"]) for row in competency_rows]

        completed = [
            task for task in tasks if task["state"] == DevelopmentState.COMPLETED.value
        ]
        active = [
            task
            for task in tasks
            if task["state"]
            in {
                DevelopmentState.RUNNING.value,
                DevelopmentState.MEASURED.value,
                DevelopmentState.REVIEW_REQUIRED.value,
            }
        ]
        queued = [
            task
            for task in tasks
            if task["state"]
            in {
                DevelopmentState.RECEIVED.value,
                DevelopmentState.PLANNED.value,
                DevelopmentState.QUEUED.value,
            }
        ]
        blocked = [
            task for task in tasks if task["state"] == DevelopmentState.BLOCKED.value
        ]
        pro_count = sum(
            item["level"] == CompetencyLevel.PRO_LEVEL.value
            and item["write_allowed"]
            for item in assessments
        )
        observer_count = sum(
            item["level"] == CompetencyLevel.OBSERVER.value
            or (
                item["level"] == CompetencyLevel.PRO_LEVEL.value
                and not item["write_allowed"]
            )
            for item in assessments
        )
        not_eligible_count = sum(
            item["level"] == CompetencyLevel.NOT_ELIGIBLE.value
            for item in assessments
        )

        next_task = queued[0] if queued else (blocked[0] if blocked else None)
        return {
            "schema_version": 1,
            "observed_at": datetime.now(UTC).isoformat(),
            "freshness_target_seconds": 10,
            "task_counts": {
                "completed": len(completed),
                "active": len(active),
                "queued": len(queued),
                "blocked": len(blocked),
            },
            "completed": completed,
            "active": active,
            "queued": queued,
            "blocked": blocked,
            "next_task": next_task,
            "competency": {
                "total": len(assessments),
                "pro_level_write_enabled": pro_count,
                "observer_or_pending": observer_count,
                "not_eligible": not_eligible_count,
                "agents": assessments,
            },
            "release_authority": {
                "q10": "NOT_VERIFIED",
                "q11": "BLOCKED",
                "q12": "BLOCKED",
                "production": "NO-GO / NOT CERTIFIED",
                "source": "fail_closed_framework_default",
                "authority_effect": "NONE",
            },
            "scores": {
                "openssf_scorecard_current": None,
                "openssf_scorecard_target": 6.0,
                "security_level": "NOT_VERIFIED",
                "unknown_values_are_never_guessed": True,
            },
        }
