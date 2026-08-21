from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field


class MemoryFragment(BaseModel):
    memory_id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    content_ref: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    retention_score: float = Field(default=1.0, ge=0, le=1)


class ConsolidatedMemory(BaseModel):
    topic: str
    source_memory_ids: list[str]
    content_refs: list[str]
    evidence_ids: list[str]
    confidence: float = Field(ge=0, le=1)


class DreamConsolidationPolicy(BaseModel):
    minimum_fragments: int = Field(default=2, ge=2)
    minimum_retention_score: float = Field(default=0.2, ge=0, le=1)
    require_evidence: bool = True


class DreamConsolidationEngine:
    """Deterministically groups related memories without autonomous model calls."""

    def __init__(self, policy: DreamConsolidationPolicy | None = None) -> None:
        self.policy = policy or DreamConsolidationPolicy()

    def consolidate(self, fragments: list[MemoryFragment]) -> list[ConsolidatedMemory]:
        if not fragments:
            return []

        grouped: dict[str, list[MemoryFragment]] = defaultdict(list)
        for fragment in fragments:
            if fragment.retention_score < self.policy.minimum_retention_score:
                continue
            if self.policy.require_evidence and not fragment.evidence_ids:
                continue
            grouped[fragment.topic.strip().lower()].append(fragment)

        results: list[ConsolidatedMemory] = []
        for topic in sorted(grouped):
            members = sorted(grouped[topic], key=lambda item: item.memory_id)
            if len(members) < self.policy.minimum_fragments:
                continue
            evidence_ids = sorted(
                {evidence for member in members for evidence in member.evidence_ids}
            )
            confidence = sum(member.retention_score for member in members) / len(members)
            results.append(
                ConsolidatedMemory(
                    topic=topic,
                    source_memory_ids=[member.memory_id for member in members],
                    content_refs=[member.content_ref for member in members],
                    evidence_ids=evidence_ids,
                    confidence=confidence,
                )
            )
        return results
