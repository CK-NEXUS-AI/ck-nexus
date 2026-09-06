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


class CanonicalSourceKind(StrEnum):
    OWNER_INPUT = "owner_input"
    CONNECTED_SERVICE = "connected_service"
    PUBLIC_DOCUMENTATION = "public_documentation"
    PROVIDER_OUTPUT = "provider_output"
    EXECUTION_EVIDENCE = "execution_evidence"
    IMPORTED_FILE = "imported_file"
    MARKETPLACE_ARTIFACT = "marketplace_artifact"
    DERIVED_SUMMARY = "derived_summary"


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


class RetentionClass(StrEnum):
    EPHEMERAL = "EPHEMERAL"
    SESSION = "SESSION"
    OPERATIONAL = "OPERATIONAL"
    LONG_TERM = "LONG_TERM"
    USER_PINNED = "USER_PINNED"
    LEGAL_HOLD = "LEGAL_HOLD"


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_id: str
    source_class: SourceClass
    locator: str
    title: str
    retrieved_at: str
    trust_score: float
    tenant_id: str = "default"
    source_kind: CanonicalSourceKind = CanonicalSourceKind.DERIVED_SUMMARY
    language: str = "und"
    publisher: str | None = None
    author: str | None = None
    published_at: str | None = None
    rights: str = "unknown"
    source_hash: str | None = None
    producer: str = "ck-nexus"
    producer_version: str | None = None
    transformation_chain: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not self.locator.strip():
            raise ValueError("source locator is required")
        if not self.producer.strip():
            raise ValueError("producer is required")
        if not 0 <= self.trust_score <= 1:
            raise ValueError("trust_score must be 0..1")
        _parse_iso8601(self.retrieved_at)
        if self.published_at is not None:
            _parse_iso8601(self.published_at)


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
    tenant_id: str = "default"
    verification: VerificationState = VerificationState.OBSERVED
    valid_from: str | None = None
    fresh_until: str | None = None
    contradicts: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    qualifiers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise ValueError("claim_id is required")
        if not self.tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not self.subject.strip() or not self.predicate.strip() or not self.value.strip():
            raise ValueError("subject, predicate and value are required")
        if not self.source_ids:
            raise ValueError("at least one source_id is required")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be 0..1")
        _parse_iso8601(self.observed_at)
        if self.valid_from is not None:
            _parse_iso8601(self.valid_from)
        if self.fresh_until is not None:
            _parse_iso8601(self.fresh_until)


@dataclass(frozen=True, slots=True)
class ConflictGroup:
    tenant_id: str
    subject: str
    predicate: str
    claim_ids: tuple[str, ...]
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MemoryWriteProposal:
    proposal_id: str
    tenant_id: str
    content: str
    source_claim_ids: tuple[str, ...]
    scope: str
    retention_days: int
    retention_class: RetentionClass = RetentionClass.OPERATIONAL
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


def freshness_score(
    retrieved_at: str,
    *,
    now: datetime,
    half_life_days: float = 30.0,
) -> float:
    if half_life_days <= 0:
        raise ValueError("half_life_days must be > 0")
    retrieved = _parse_iso8601(retrieved_at)
    age_days = max(0.0, (now.astimezone(UTC) - retrieved).total_seconds() / 86400)
    return round(0.5 ** (age_days / half_life_days), 6)


class KnowledgeFabric:
    """Provenance and retrieval layer extending the existing IdeaGraph.

    Ranking metadata never grants verification or release authority. Tenant and
    revocation filters are applied before ranking to prevent cross-boundary
    retrieval.
    """

    _FORBIDDEN_MEMORY_SCOPES = {"policy", "approval", "release_gate", "credential"}

    def __init__(self) -> None:
        self.sources: dict[str, SourceRecord] = {}
        self.claims: dict[str, KnowledgeClaim] = {}
        self._revoked_source_ids: set[str] = set()

    def add_source(self, source: SourceRecord) -> SourceRecord:
        existing = self.sources.get(source.source_id)
        if existing is not None:
            if existing == source:
                return existing
            if (
                existing.tenant_id == source.tenant_id
                and existing.source_hash
                and existing.source_hash == source.source_hash
            ):
                return existing
            raise ValueError("source_id already exists with different content or metadata")
        self.sources[source.source_id] = source
        return source

    def revoke_source(self, source_id: str) -> None:
        if source_id not in self.sources:
            raise KeyError("unknown source_id")
        self._revoked_source_ids.add(source_id)

    def restore_source(self, source_id: str) -> None:
        if source_id not in self.sources:
            raise KeyError("unknown source_id")
        self._revoked_source_ids.discard(source_id)

    def source_is_active(self, source_id: str) -> bool:
        if source_id not in self.sources:
            raise KeyError("unknown source_id")
        return source_id not in self._revoked_source_ids

    def add_claim(self, claim: KnowledgeClaim) -> KnowledgeClaim:
        if claim.claim_id in self.claims:
            raise ValueError("claim_id already exists")
        missing = [source_id for source_id in claim.source_ids if source_id not in self.sources]
        if missing:
            raise ValueError("unknown source_ids: " + ", ".join(sorted(missing)))
        wrong_tenant = [
            source_id
            for source_id in claim.source_ids
            if self.sources[source_id].tenant_id != claim.tenant_id
        ]
        if wrong_tenant:
            raise ValueError("claim cannot reference sources from another tenant")
        for related_id in (*claim.contradicts, *claim.supersedes):
            related = self.claims.get(related_id)
            if related is None:
                raise ValueError(f"unknown related claim id: {related_id}")
            if related.tenant_id != claim.tenant_id:
                raise ValueError("claim relationship cannot cross tenant boundary")
        self.claims[claim.claim_id] = claim
        return claim

    def conflict_groups(self, *, tenant_id: str | None = None) -> tuple[ConflictGroup, ...]:
        grouped: dict[tuple[str, str, str], list[KnowledgeClaim]] = {}
        for claim in self.claims.values():
            if tenant_id is not None and claim.tenant_id != tenant_id:
                continue
            grouped.setdefault(
                (claim.tenant_id, _key(claim.subject), _key(claim.predicate)), []
            ).append(claim)

        conflicts: list[ConflictGroup] = []
        for claims in grouped.values():
            values = {_key(claim.value) for claim in claims}
            explicitly_conflicted = any(claim.contradicts for claim in claims)
            if len(values) <= 1 and not explicitly_conflicted:
                continue
            ordered = sorted(claims, key=lambda claim: claim.claim_id)
            conflicts.append(
                ConflictGroup(
                    tenant_id=ordered[0].tenant_id,
                    subject=ordered[0].subject,
                    predicate=ordered[0].predicate,
                    claim_ids=tuple(claim.claim_id for claim in ordered),
                    values=tuple(claim.value for claim in ordered),
                )
            )
        return tuple(
            sorted(conflicts, key=lambda item: (item.tenant_id, item.subject, item.predicate))
        )

    def claim_is_fresh(self, claim: KnowledgeClaim, *, now: datetime) -> bool:
        if claim.fresh_until is None:
            return True
        return now.astimezone(UTC) <= _parse_iso8601(claim.fresh_until)

    def claim_is_retrieval_eligible(self, claim: KnowledgeClaim, *, now: datetime) -> bool:
        if not self.claim_is_fresh(claim, now=now):
            return False
        return all(self.source_is_active(source_id) for source_id in claim.source_ids)

    def source_weight(self, claim: KnowledgeClaim, *, now: datetime) -> float:
        if not self.claim_is_retrieval_eligible(claim, now=now):
            return 0.0
        source_scores: list[float] = []
        for source_id in claim.source_ids:
            source = self.sources[source_id]
            freshness = freshness_score(source.retrieved_at, now=now)
            source_scores.append(source.trust_score * freshness)
        if not source_scores:
            return 0.0
        return round((sum(source_scores) / len(source_scores)) * claim.confidence, 6)

    def retrieval_candidates(
        self,
        *,
        tenant_id: str,
        now: datetime,
        minimum_weight: float = 0.0,
    ) -> tuple[KnowledgeClaim, ...]:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not 0 <= minimum_weight <= 1:
            raise ValueError("minimum_weight must be 0..1")
        ranked: list[tuple[float, str, KnowledgeClaim]] = []
        for claim in self.claims.values():
            if claim.tenant_id != tenant_id:
                continue
            weight = self.source_weight(claim, now=now)
            if weight > 0 and weight >= minimum_weight:
                ranked.append((weight, claim.claim_id, claim))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return tuple(item[2] for item in ranked)

    def synthesis_view(self, *, tenant_id: str | None = None) -> SynthesisView:
        by_class: dict[ClaimClass, list[KnowledgeClaim]] = {
            claim_class: [] for claim_class in ClaimClass
        }
        for claim in self.claims.values():
            if tenant_id is not None and claim.tenant_id != tenant_id:
                continue
            by_class[claim.claim_class].append(claim)
        for claims in by_class.values():
            claims.sort(key=lambda claim: claim.claim_id)
        return SynthesisView(
            facts=tuple(by_class[ClaimClass.FACT]),
            opinions=tuple(by_class[ClaimClass.OPINION]),
            inferences=tuple(by_class[ClaimClass.INFERENCE]),
            predictions=tuple(by_class[ClaimClass.PREDICTION]),
            assumptions=tuple(by_class[ClaimClass.ASSUMPTION]),
            conflicts=self.conflict_groups(tenant_id=tenant_id),
        )

    def propose_memory_write(
        self,
        *,
        content: str,
        source_claim_ids: tuple[str, ...],
        scope: str,
        retention_days: int,
        retention_class: RetentionClass = RetentionClass.OPERATIONAL,
        tenant_id: str = "default",
    ) -> MemoryWriteProposal:
        normalized_scope = _key(scope).replace(" ", "_")
        if normalized_scope in self._FORBIDDEN_MEMORY_SCOPES:
            raise PermissionError("knowledge fabric cannot mutate protected authority scope")
        if not tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not content.strip():
            raise ValueError("memory content is required")
        if retention_days <= 0:
            raise ValueError("retention_days must be > 0")
        missing = [claim_id for claim_id in source_claim_ids if claim_id not in self.claims]
        if missing:
            raise ValueError("unknown source claim ids: " + ", ".join(sorted(missing)))
        wrong_tenant = [
            claim_id
            for claim_id in source_claim_ids
            if self.claims[claim_id].tenant_id != tenant_id
        ]
        if wrong_tenant:
            raise ValueError("memory proposal cannot reference claims from another tenant")
        return MemoryWriteProposal(
            proposal_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            content=content,
            source_claim_ids=source_claim_ids,
            scope=scope,
            retention_days=retention_days,
            retention_class=retention_class,
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
            tags=["knowledge-fabric", claim.claim_class.value, f"tenant:{claim.tenant_id}"],
            source_refs=list(claim.source_ids),
            confidence=claim.confidence,
            raw_input="",
        )
