from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class MemoryDecayPolicy(BaseModel):
    half_life_hours: float = Field(default=168.0, gt=0)
    access_boost: float = Field(default=0.04, ge=0, le=1)
    importance_weight: float = Field(default=0.35, ge=0, le=1)
    minimum_score: float = Field(default=0.05, ge=0, le=1)


class MemoryDecayInput(BaseModel):
    created_at: datetime
    last_accessed_at: datetime
    access_count: int = Field(default=0, ge=0)
    importance: float = Field(default=0.5, ge=0, le=1)
    protected: bool = False


class MemoryDecayResult(BaseModel):
    retention_score: float = Field(ge=0, le=1)
    expired: bool
    age_hours: float = Field(ge=0)
    idle_hours: float = Field(ge=0)


class MemoryDecayEngine:
    """Scores retention deterministically using caller-supplied time."""

    def __init__(self, policy: MemoryDecayPolicy | None = None) -> None:
        self.policy = policy or MemoryDecayPolicy()

    def evaluate(
        self,
        memory: MemoryDecayInput,
        *,
        now: datetime,
    ) -> MemoryDecayResult:
        current = self._normalize(now)
        created = self._normalize(memory.created_at)
        accessed = self._normalize(memory.last_accessed_at)
        if created > current or accessed > current:
            raise ValueError("memory timestamps cannot be in the future")
        if accessed < created:
            raise ValueError("last_accessed_at cannot predate created_at")

        age_hours = (current - created).total_seconds() / 3600
        idle_hours = (current - accessed).total_seconds() / 3600
        if memory.protected:
            return MemoryDecayResult(
                retention_score=1.0,
                expired=False,
                age_hours=age_hours,
                idle_hours=idle_hours,
            )

        time_score = 0.5 ** (idle_hours / self.policy.half_life_hours)
        access_score = min(1.0, memory.access_count * self.policy.access_boost)
        weighted_importance = memory.importance * self.policy.importance_weight
        score = min(1.0, time_score + access_score + weighted_importance)
        return MemoryDecayResult(
            retention_score=score,
            expired=score < self.policy.minimum_score,
            age_hours=age_hours,
            idle_hours=idle_hours,
        )

    @staticmethod
    def _normalize(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("memory timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)
