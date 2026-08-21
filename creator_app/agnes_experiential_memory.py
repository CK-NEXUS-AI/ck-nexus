from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import uuid4

from creator_app.agnes_ledger import AppendOnlyLedger


class ExperienceResult(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"


class ValidityStatus(StrEnum):
    VALID = "VALID"
    SUPERSEDED = "SUPERSEDED"
    INVALIDATED = "INVALIDATED"


@dataclass(frozen=True, slots=True)
class ExperienceEntry:
    experience_id: str
    task_type: str
    context_digest: str
    action_strategy: str
    result: ExperienceResult
    failure_reason: str | None
    lesson: str
    confidence: float
    verified_by: str
    source_run: str | None
    evidence_links: tuple[str, ...]
    created_at: str
    validity_status: ValidityStatus = ValidityStatus.VALID
    supersedes: str | None = None
    last_validated: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "experience_id": self.experience_id,
            "task_type": self.task_type,
            "context_digest": self.context_digest,
            "action_strategy": self.action_strategy,
            "result": self.result.value,
            "failure_reason": self.failure_reason,
            "lesson": self.lesson,
            "confidence": self.confidence,
            "verified_by": self.verified_by,
            "created_at": self.created_at,
            "supersedes": self.supersedes,
            "provenance": {
                "source_run": self.source_run,
                "evidence_links": list(self.evidence_links),
                "validity_status": self.validity_status.value,
                "last_validated": self.last_validated,
            },
        }


class ExperientialMemory:
    """Append-only AGNES experience memory with provenance and supersession.

    Raw task context is deliberately not accepted. Callers must provide a digest.
    This store records lessons/provenance; it does not grant execution authority.
    """

    EVENT_RECORDED = "experience_recorded"
    EVENT_VALIDATED = "experience_validated"
    EVENT_SUPERSEDED = "experience_superseded"
    EVENT_INVALIDATED = "experience_invalidated"

    def __init__(self, ledger: AppendOnlyLedger) -> None:
        self.ledger = ledger

    @staticmethod
    def digest_context(value: str | bytes) -> str:
        raw = value.encode("utf-8") if isinstance(value, str) else value
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _require_digest(value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(
            ch not in "0123456789abcdef" for ch in normalized
        ):
            raise ValueError("context_digest must be a 64-character SHA-256 hex digest")
        return normalized

    @staticmethod
    def _verified_by(value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("verified_by is required")
        if normalized.lower() in {"agnes", "self", "self_verifier", "self-approval"}:
            raise ValueError("AGNES cannot self-verify or self-approve learning")
        return normalized

    @staticmethod
    def _confidence(value: float) -> float:
        number = float(value)
        if not 0.0 <= number <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return number

    def _events(self) -> list[dict[str, Any]]:
        if not self.ledger.path.exists():
            return []
        verified = self.ledger.verify()
        if not verified.valid:
            raise RuntimeError(f"experience ledger integrity failure: {verified.error}")
        events: list[dict[str, Any]] = []
        with self.ledger.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if str(row.get("event_type", "")).startswith("experience_"):
                    events.append(row)
        return events

    def _state(self) -> dict[str, ExperienceEntry]:
        entries: dict[str, ExperienceEntry] = {}
        for event in self._events():
            payload = event.get("payload", {})
            event_type = event.get("event_type")
            experience_id = str(payload.get("experience_id") or "")
            if event_type == self.EVENT_RECORDED:
                entries[experience_id] = ExperienceEntry(
                    experience_id=experience_id,
                    task_type=str(payload["task_type"]),
                    context_digest=str(payload["context_digest"]),
                    action_strategy=str(payload["action_strategy"]),
                    result=ExperienceResult(str(payload["result"])),
                    failure_reason=payload.get("failure_reason"),
                    lesson=str(payload["lesson"]),
                    confidence=float(payload["confidence"]),
                    verified_by=str(payload["verified_by"]),
                    source_run=payload.get("source_run"),
                    evidence_links=tuple(payload.get("evidence_links", ())),
                    created_at=str(event.get("at") or ""),
                    supersedes=payload.get("supersedes"),
                )
                continue
            current = entries.get(experience_id)
            if current is None:
                continue
            data = current.as_dict()
            provenance = data["provenance"]
            if event_type == self.EVENT_VALIDATED:
                provenance["validity_status"] = ValidityStatus.VALID.value
                provenance["last_validated"] = str(
                    payload.get("validated_at") or event.get("at")
                )
                data["verified_by"] = str(
                    payload.get("verified_by") or current.verified_by
                )
                if payload.get("evidence_links"):
                    provenance["evidence_links"] = list(payload["evidence_links"])
            elif event_type == self.EVENT_SUPERSEDED:
                provenance["validity_status"] = ValidityStatus.SUPERSEDED.value
            elif event_type == self.EVENT_INVALIDATED:
                provenance["validity_status"] = ValidityStatus.INVALIDATED.value
            entries[experience_id] = self._from_dict(data)
        return entries

    @staticmethod
    def _from_dict(data: dict[str, Any]) -> ExperienceEntry:
        provenance = data["provenance"]
        return ExperienceEntry(
            experience_id=str(data["experience_id"]),
            task_type=str(data["task_type"]),
            context_digest=str(data["context_digest"]),
            action_strategy=str(data["action_strategy"]),
            result=ExperienceResult(str(data["result"])),
            failure_reason=data.get("failure_reason"),
            lesson=str(data["lesson"]),
            confidence=float(data["confidence"]),
            verified_by=str(data["verified_by"]),
            source_run=provenance.get("source_run"),
            evidence_links=tuple(provenance.get("evidence_links", ())),
            created_at=str(data["created_at"]),
            validity_status=ValidityStatus(str(provenance["validity_status"])),
            supersedes=data.get("supersedes"),
            last_validated=provenance.get("last_validated"),
        )

    def record_experience(
        self,
        *,
        task_type: str,
        context_digest: str,
        action_strategy: str,
        result: ExperienceResult | str,
        lesson: str,
        confidence: float,
        verified_by: str,
        source_run: str | None = None,
        evidence_links: list[str] | tuple[str, ...] = (),
        failure_reason: str | None = None,
        supersedes: str | None = None,
    ) -> ExperienceEntry:
        digest = self._require_digest(context_digest)
        state = self._state()
        if supersedes and supersedes not in state:
            raise KeyError(f"unknown superseded experience: {supersedes}")
        experience_id = f"exp_{uuid4().hex}"
        payload = {
            "experience_id": experience_id,
            "task_type": task_type.strip(),
            "context_digest": digest,
            "action_strategy": action_strategy.strip(),
            "result": ExperienceResult(result).value,
            "failure_reason": failure_reason,
            "lesson": lesson.strip(),
            "confidence": self._confidence(confidence),
            "verified_by": self._verified_by(verified_by),
            "source_run": source_run,
            "evidence_links": list(evidence_links),
            "supersedes": supersedes,
            "authority": "learning_only_no_execution_grant",
        }
        if (
            not payload["task_type"]
            or not payload["action_strategy"]
            or not payload["lesson"]
        ):
            raise ValueError("task_type, action_strategy and lesson are required")
        row = self.ledger.append(self.EVENT_RECORDED, payload)
        payload["created_at"] = str(row["at"])
        entry = self._from_dict(
            {
                **payload,
                "provenance": {
                    "source_run": source_run,
                    "evidence_links": list(evidence_links),
                    "validity_status": ValidityStatus.VALID.value,
                    "last_validated": None,
                },
            }
        )
        if supersedes:
            self.supersede_experience(
                supersedes, experience_id, verified_by=verified_by
            )
        return entry

    def retrieve_relevant(
        self, *, task_type: str, limit: int = 5
    ) -> list[ExperienceEntry]:
        candidates = [
            entry
            for entry in self._state().values()
            if entry.task_type == task_type
            and entry.validity_status is ValidityStatus.VALID
        ]
        candidates.sort(
            key=lambda item: (item.confidence, item.created_at), reverse=True
        )
        return candidates[: max(0, limit)]

    def validate_provenance(
        self,
        experience_id: str,
        *,
        verified_by: str,
        evidence_links: list[str] | tuple[str, ...] = (),
    ) -> ExperienceEntry:
        state = self._state()
        if experience_id not in state:
            raise KeyError(experience_id)
        row = self.ledger.append(
            self.EVENT_VALIDATED,
            {
                "experience_id": experience_id,
                "verified_by": self._verified_by(verified_by),
                "evidence_links": list(evidence_links),
            },
        )
        updated = self._state()[experience_id]
        if updated.last_validated is None:
            raise RuntimeError(f"validation event was not applied: {row['hash']}")
        return updated

    def supersede_experience(
        self, old_id: str, new_id: str, *, verified_by: str
    ) -> ExperienceEntry:
        state = self._state()
        if old_id not in state or new_id not in state:
            raise KeyError("old and new experience must already exist")
        if old_id == new_id:
            raise ValueError("an experience cannot supersede itself")
        self.ledger.append(
            self.EVENT_SUPERSEDED,
            {
                "experience_id": old_id,
                "superseded_by": new_id,
                "verified_by": self._verified_by(verified_by),
            },
        )
        return self._state()[old_id]

    def invalidate_experience(
        self, experience_id: str, *, verified_by: str, reason: str
    ) -> ExperienceEntry:
        if experience_id not in self._state():
            raise KeyError(experience_id)
        self.ledger.append(
            self.EVENT_INVALIDATED,
            {
                "experience_id": experience_id,
                "verified_by": self._verified_by(verified_by),
                "reason": reason.strip(),
            },
        )
        return self._state()[experience_id]

    def build_provenance_graph(self) -> dict[str, object]:
        entries = self._state()
        nodes = [entry.as_dict() for entry in entries.values()]
        edges: list[dict[str, str]] = []
        for entry in entries.values():
            if entry.source_run:
                edges.append(
                    {
                        "from": entry.source_run,
                        "to": entry.experience_id,
                        "type": "SOURCE_RUN",
                    }
                )
            for ref in entry.evidence_links:
                edges.append(
                    {"from": ref, "to": entry.experience_id, "type": "EVIDENCE"}
                )
            if entry.supersedes:
                edges.append(
                    {
                        "from": entry.experience_id,
                        "to": entry.supersedes,
                        "type": "SUPERSEDES",
                    }
                )
        return {
            "nodes": nodes,
            "edges": edges,
            "ledger": self.ledger.verify().as_dict(),
        }
