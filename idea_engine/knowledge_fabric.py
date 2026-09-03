from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from .models import IdeaNode, NodeType


class SourceClass(StrEnum):
    USER = "user"
    INTERNAL = "internal"
    WEB = "web"
    RESEARCH = "research"
    COMMUNITY = "community"
    PROFESSIONAL = "professional"
    TOOL = "tool"


class ClaimClass(StrEnum):
    FACT = "fact"
    OPINION = "opinion"
    INFERENCE = "inference"
    PREDICTION = "prediction"
    ASSUMPTION = "assumption"


class VerificationState(StrEnum):
    OBSERVED = "observed"
    MEASURED_NOT_VERIFIED = "measured_not_verified"
    VERIFIED = "verified"
    CONFLICTED = "conflicted"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: str
    source_class: SourceClass
    locator: str
    title: str
    retrieved_at: str
    trust_score: float
    language: str = "und"
    publisher: str | None = None
    author: str | None = None
    published_at: str | None = None
    rights: str = "unknown"
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.locator.strip():
            raise ValueError("source locator is required")
        if not 0 <= self.trust_score <= 1:
            raise ValueError("trust_score must be 0..1")


@dataclass(frozen=True, slots=True)
class KnowledgeClaim:
    claim_id: str
    subject: str
    predicate: str
    value: str
    claim_class: ClaimClass
    source_ids: tuple[str, ...]
    confidence: float
    observed_at: str
    verification: VerificationState = VerificationState.OBSERVED
    qualifiers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise ValueError("claim_id is required")
        if not self.subject.strip() or not self.predicate.strip() or not self.value.strip():
            raise ValueError("subject, predicate and value are required")
        if not self.source_ids:
            raise ValueError("at least one source_id is required")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be 0..1")


@dataclass(frozen=True, slots=True)
class ConflictGroup:
    subject: str
    predicate: str
    claim_ids: tuple[str, ...]
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MemoryWriteProposal:
    proposal_id: str
    content: str
    source_claim_ids: tuple[str, ...]
    scope: str
    retention_days: int
    consent_required: bool = True
    auto_approved: bool = False


@dataclass(frozen=True, slots=True)
class SynthesisView:
    facts: tuple[KnowledgeClaim, ...]
    opinions: tuple[KnowledgeClaim, ...]
    inferences: tuple[KnowledgeClaim, ...]
    predictions: tuple[KnowledgeClaim, ...]
    assumptions: tuple[KnowledgeClaim, ...]
    conflicts: tuple[ConflictGroup, ...]


def _key(value: str) -> str:
    return " ".join(value.casefold().split())


def _parse_iso8601(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def freshness_score(retrieved_at: str, *, now: datetime, half_life_days: float = 30.0) -> float:
    if half_life_days <= 0:
        raise ValueError("half_life_days must be > 0")
    retrieved = _parse_iso8601(retrieved_at)
    age_days = max(0.0, (now.astimezone(UTC) - retrieved).total_seconds() / 86400)
    return round(0.5 ** (age_days / half_life_days), 6)


class KnowledgeFabric:
    """Deterministic provenance layer that extends, rather than replaces, IdeaGraph."""

    _FORBIDDEN_MEMORY_SCOPES = {"policy", "approval", "release_gate", "credential"}

    def __init__(self) -> None:
        self.sources: dict[str, SourceRecord] = {}
        self.claims: dict[str, KnowledgeClaim] = {}

    def add_source(self, source: SourceRecord) -> SourceRecord:
        if source.source_id in self.sources:
            raise ValueError("source_id already exists")
        self.sources[source.source_id] = source
        return source

    def add_claim(self, claim: KnowledgeClaim) -> KnowledgeClaim:
        if claim.claim_id in self.claims:
            raise ValueError("claim_id already exists")
        missing = [source_id for source_id in claim.source_ids if source_id not in self.sources]
        if missing:
            raise ValueError("unknown source_ids: " + ", ".join(sorted(missing)))
        self.claims[claim.claim_id] = claim
        return claim

    def conflict_groups(self) -> tuple[ConflictGroup, ...]:
        grouped: dict[tuple[str, str], list[KnowledgeClaim]] = {}
        for claim in self.claims.values():
            grouped.setdefault((_key(claim.subject), _key(claim.predicate)), []).append(claim)

        conflicts: list[ConflictGroup] = []
        for claims in grouped.values():
            values = {_key(claim.value) for claim in claims}
            if len(values) <= 1:
                continue
            ordered = sorted(claims, key=lambda claim: claim.claim_id)
            conflicts.append(
                ConflictGroup(
                    subject=ordered[0].subject,
                    predicate=ordered[0].predicate,
                    claim_ids=tuple(claim.claim_id for claim in ordered),
                    values=tuple(claim.value for claim in ordered),
                )
            )
        return tuple(sorted(conflicts, key=lambda item: (item.subject, item.predicate)))

    def source_weight(self, claim: KnowledgeClaim, *, now: datetime) -> float:
        source_scores: list[float] = []
        for source_id in claim.source_ids:
            source = self.sources[source_id]
            freshness = freshness_score(source.retrieved_at, now=now)
            source_scores.append(source.trust_score * freshness)
        if not source_scores:
            return 0.0
        return round((sum(source_scores) / len(source_scores)) * claim.confidence, 6)

    def synthesis_view(self) -> SynthesisView:
        by_class: dict[ClaimClass, list[KnowledgeClaim]] = {
            claim_class: [] for claim_class in ClaimClass
        }
        for claim in self.claims.values():
            by_class[claim.claim_class].append(claim)
        for claims in by_class.values():
            claims.sort(key=lambda claim: claim.claim_id)
        return SynthesisView(
            facts=tuple(by_class[ClaimClass.FACT]),
            opinions=tuple(by_class[ClaimClass.OPINION]),
            inferences=tuple(by_class[ClaimClass.INFERENCE]),
            predictions=tuple(by_class[ClaimClass.PREDICTION]),
            assumptions=tuple(by_class[ClaimClass.ASSUMPTION]),
            conflicts=self.conflict_groups(),
        )

    def propose_memory_write(
        self,
        *,
        content: str,
        source_claim_ids: tuple[str, ...],
        scope: str,
        retention_days: int,
    ) -> MemoryWriteProposal:
        normalized_scope = _key(scope).replace(" ", "_")
        if normalized_scope in self._FORBIDDEN_MEMORY_SCOPES:
            raise PermissionError("knowledge fabric cannot mutate protected authority scope")
        if not content.strip():
            raise ValueError("memory content is required")
        if retention_days <= 0:
            raise ValueError("retention_days must be > 0")
        missing = [claim_id for claim_id in source_claim_ids if claim_id not in self.claims]
        if missing:
            raise ValueError("unknown source claim ids: " + ", ".join(sorted(missing)))
        return MemoryWriteProposal(
            proposal_id=str(uuid.uuid4()),
            content=content,
            source_claim_ids=source_claim_ids,
            scope=scope,
            retention_days=retention_days,
        )

    def claim_to_idea_node(self, claim_id: str) -> IdeaNode:
        claim = self.claims[claim_id]
        node_type = (
            NodeType.EVIDENCE.value
            if claim.claim_class is ClaimClass.FACT
            else NodeType.ASSUMPTION.value
        )
        return IdeaNode(
            id=f"knowledge:{claim.claim_id}",
            type=node_type,
            title=f"{claim.subject} / {claim.predicate}",
            summary=claim.value,
            status=claim.verification.value,
            tags=["knowledge-fabric", claim.claim_class.value],
            source_refs=list(claim.source_ids),
            confidence=claim.confidence,
            raw_input="",
        )
