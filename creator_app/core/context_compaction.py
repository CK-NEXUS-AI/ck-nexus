from __future__ import annotations

from pydantic import BaseModel, Field


class ContextSegment(BaseModel):
    segment_id: str
    token_count: int = Field(ge=0)
    importance: float = Field(ge=0.0, le=1.0)
    pinned: bool = False
    contains_policy: bool = False
    contains_evidence_reference: bool = False


class CompactionDecision(BaseModel):
    keep_ids: list[str]
    compact_ids: list[str]
    total_tokens_before: int
    estimated_tokens_after: int
    policy_preserved: bool
    evidence_references_preserved: bool


class ContextCompactionPolicy:
    """Provider-neutral compaction planner that preserves authority context."""

    def plan(
        self,
        *,
        segments: list[ContextSegment],
        target_tokens: int,
    ) -> CompactionDecision:
        if target_tokens < 0:
            raise ValueError("target_tokens must be non-negative")

        protected = {
            item.segment_id
            for item in segments
            if item.pinned or item.contains_policy or item.contains_evidence_reference
        }
        ordered = sorted(
            segments,
            key=lambda item: (item.segment_id not in protected, -item.importance),
        )

        keep_ids: list[str] = []
        compact_ids: list[str] = []
        used = 0
        for item in ordered:
            if item.segment_id in protected or used + item.token_count <= target_tokens:
                keep_ids.append(item.segment_id)
                used += item.token_count
            else:
                compact_ids.append(item.segment_id)

        total = sum(item.token_count for item in segments)
        policy_ids = {item.segment_id for item in segments if item.contains_policy}
        evidence_ids = {
            item.segment_id for item in segments if item.contains_evidence_reference
        }
        return CompactionDecision(
            keep_ids=keep_ids,
            compact_ids=compact_ids,
            total_tokens_before=total,
            estimated_tokens_after=used,
            policy_preserved=policy_ids.issubset(keep_ids),
            evidence_references_preserved=evidence_ids.issubset(keep_ids),
        )
