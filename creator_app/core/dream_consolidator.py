from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ConsolidationAction(StrEnum):
    KEEP = "keep"
    MERGE = "merge"
    SUPERSEDE = "supersede"
    SYNTHESIZE = "synthesize"
    BLOCK = "block"


class MemoryCandidate(BaseModel):
    memory_id: str
    content_digest: str
    source_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0, le=1)


class ConsolidationDecision(BaseModel):
    action: ConsolidationAction
    input_ids: list[str] = Field(default_factory=list)
    output_digest: str | None = None
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)

    @property
    def promotable(self) -> bool:
        if self.action in {
            ConsolidationAction.MERGE,
            ConsolidationAction.SUPERSEDE,
            ConsolidationAction.SYNTHESIZE,
        }:
            return bool(self.output_digest and self.evidence_ids and self.reason.strip())
        return self.action == ConsolidationAction.KEEP and bool(self.reason.strip())


class DreamConsolidator:
    """Plans background memory consolidation without mutating source history."""

    def decide_duplicate(
        self,
        left: MemoryCandidate,
        right: MemoryCandidate,
        *,
        evidence_ids: list[str],
    ) -> ConsolidationDecision:
        if not evidence_ids:
            return ConsolidationDecision(
                action=ConsolidationAction.BLOCK,
                input_ids=[left.memory_id, right.memory_id],
                reason="duplicate merge requires evidence",
            )
        if left.content_digest != right.content_digest:
            return ConsolidationDecision(
                action=ConsolidationAction.KEEP,
                input_ids=[left.memory_id, right.memory_id],
                reason="digests differ; preserve both memories",
                evidence_ids=evidence_ids,
            )
        return ConsolidationDecision(
            action=ConsolidationAction.MERGE,
            input_ids=[left.memory_id, right.memory_id],
            output_digest=left.content_digest,
            reason="identical content digests",
            evidence_ids=evidence_ids,
        )

    def supersede(
        self,
        *,
        stale_memory_id: str,
        replacement_digest: str,
        evidence_ids: list[str],
    ) -> ConsolidationDecision:
        if not replacement_digest or not evidence_ids:
            return ConsolidationDecision(
                action=ConsolidationAction.BLOCK,
                input_ids=[stale_memory_id],
                reason="supersession requires replacement digest and evidence",
            )
        return ConsolidationDecision(
            action=ConsolidationAction.SUPERSEDE,
            input_ids=[stale_memory_id],
            output_digest=replacement_digest,
            reason="replacement is evidence-backed; preserve stale history as superseded",
            evidence_ids=evidence_ids,
        )
