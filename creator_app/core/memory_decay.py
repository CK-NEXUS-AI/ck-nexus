from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MemoryKind(StrEnum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryRecord(BaseModel):
    memory_id: str
    kind: MemoryKind
    content_digest: str
    created_at: datetime
    last_retrieved_at: datetime | None = None
    retrieval_count: int = Field(default=0, ge=0)
    importance: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=1.0, ge=0, le=1)
    superseded_by: str | None = None


class MemoryDecayPolicy(BaseModel):
    half_life_days: float = Field(default=30.0, gt=0)
    retrieval_reinforcement: float = Field(default=0.08, ge=0, le=1)
    minimum_score: float = Field(default=0.05, ge=0, le=1)

    def score(self, memory: MemoryRecord, *, now: datetime | None = None) -> float:
        """Return a bounded temporal ranking score without deleting history."""
        current = now or datetime.now(UTC)
        return self.score_at(memory, now=current)

    def score_at(self, memory: MemoryRecord, *, now: datetime) -> float:
        """Score deterministically with a caller-supplied timezone-aware clock."""
        if now.tzinfo is None:
            raise ValueError("memory scoring clock must be timezone-aware")
        if memory.created_at.tzinfo is None:
            raise ValueError("memory created_at must be timezone-aware")
        if memory.last_retrieved_at is not None and memory.last_retrieved_at.tzinfo is None:
            raise ValueError("memory last_retrieved_at must be timezone-aware")
        current = now.astimezone(UTC)
        anchor = (memory.last_retrieved_at or memory.created_at).astimezone(UTC)
        if anchor > current:
            raise ValueError("memory timestamp cannot be in the future")
        age_days = (current - anchor).total_seconds() / 86400
        decay = 0.5 ** (age_days / self.half_life_days)
        reinforcement = min(memory.retrieval_count * self.retrieval_reinforcement, 1.0)
        score = decay * memory.importance * memory.confidence + reinforcement
        if memory.superseded_by:
            score *= 0.25
        return max(self.minimum_score, min(score, 1.0))
