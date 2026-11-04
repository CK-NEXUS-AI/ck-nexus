from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any
from uuid import uuid4


class BlackboardEntryType(StrEnum):
    GOAL = "goal"
    CLAIM = "claim"
    EVIDENCE = "evidence"
    HYPOTHESIS = "hypothesis"
    QUESTION = "question"
    CONTRADICTION = "contradiction"
    ARTIFACT = "artifact"
    TASK = "task"
    STATE = "state"
    PROPOSAL = "proposal"


@dataclass(frozen=True, slots=True)
class BlackboardEntry:
    entry_id: str
    entry_type: BlackboardEntryType
    author: str
    content: str
    created_at: datetime
    correlation_id: str | None = None
    causation_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    content_digest: str = ""


class CognitiveBlackboard:
    """Append-only shared cognitive state.

    The blackboard never grants execution authority. Agents can publish observations,
    proposals and evidence references; a separate governor must authorize mutations in
    external systems.
    """

    def __init__(self) -> None:
        self._entries: list[BlackboardEntry] = []

    def append(
        self,
        *,
        entry_type: BlackboardEntryType,
        author: str,
        content: str,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        evidence_refs: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> BlackboardEntry:
        if not author.strip():
            raise ValueError("author is required")
        if not content.strip():
            raise ValueError("content is required")
        digest = sha256(content.encode("utf-8")).hexdigest()
        entry = BlackboardEntry(
            entry_id=f"bb-{uuid4().hex}",
            entry_type=entry_type,
            author=author.strip(),
            content=content,
            created_at=datetime.now(UTC),
            correlation_id=correlation_id,
            causation_id=causation_id,
            evidence_refs=tuple(evidence_refs),
            metadata=dict(metadata or {}),
            content_digest=digest,
        )
        self._entries.append(entry)
        return entry

    def entries(
        self,
        *,
        entry_type: BlackboardEntryType | None = None,
        correlation_id: str | None = None,
    ) -> tuple[BlackboardEntry, ...]:
        items = self._entries
        if entry_type is not None:
            items = [item for item in items if item.entry_type is entry_type]
        if correlation_id is not None:
            items = [item for item in items if item.correlation_id == correlation_id]
        return tuple(items)

    def contradictions(self) -> tuple[BlackboardEntry, ...]:
        return self.entries(entry_type=BlackboardEntryType.CONTRADICTION)

    def latest(self, entry_type: BlackboardEntryType) -> BlackboardEntry | None:
        for item in reversed(self._entries):
            if item.entry_type is entry_type:
                return item
        return None

    def snapshot(self) -> tuple[BlackboardEntry, ...]:
        return tuple(self._entries)
