from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SourceTrust(StrEnum):
    VERIFIED = "verified"
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class CitationRelation(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXT = "context"


class ClaimStatus(StrEnum):
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    BLOCKED = "blocked"


class CitationSource(BaseModel):
    source_id: str
    publisher_id: str
    artifact_digest: str
    trust: SourceTrust = SourceTrust.UNTRUSTED
    evidence_ids: tuple[str, ...] = ()


class ClaimNode(BaseModel):
    claim_id: str
    statement_digest: str


class CitationEdge(BaseModel):
    claim_id: str
    source_id: str
    relation: CitationRelation
    excerpt_digest: str
    verified: bool = False
    evidence_ids: tuple[str, ...] = ()


class ClaimVerification(BaseModel):
    claim_id: str
    status: ClaimStatus
    verified_source_ids: tuple[str, ...] = ()
    independent_publishers: int = Field(default=0, ge=0)
    evidence_ids: tuple[str, ...] = ()


class CitationPolicy(BaseModel):
    minimum_verified_sources: int = Field(default=2, ge=1, le=20)
    minimum_independent_publishers: int = Field(default=2, ge=1, le=20)


class CitationGraph:
    """Digest-only claim/source graph with deterministic claim-level verification."""

    def __init__(self, policy: CitationPolicy | None = None) -> None:
        self.policy = policy or CitationPolicy()
        self._sources: dict[str, CitationSource] = {}
        self._claims: dict[str, ClaimNode] = {}
        self._edges: list[CitationEdge] = []

    def add_source(self, source: CitationSource) -> None:
        if source.source_id in self._sources:
            raise ValueError("duplicate_source_id")
        self._sources[source.source_id] = source

    def add_claim(self, claim: ClaimNode) -> None:
        if claim.claim_id in self._claims:
            raise ValueError("duplicate_claim_id")
        self._claims[claim.claim_id] = claim

    def add_edge(self, edge: CitationEdge) -> None:
        if edge.claim_id not in self._claims:
            raise ValueError("unknown_claim")
        if edge.source_id not in self._sources:
            raise ValueError("unknown_source")
        self._edges.append(edge)

    def verify_claim(self, claim_id: str) -> ClaimVerification:
        if claim_id not in self._claims:
            raise ValueError("unknown_claim")

        relevant = [edge for edge in self._edges if edge.claim_id == claim_id]
        verified = [
            edge
            for edge in relevant
            if edge.verified and edge.evidence_ids and self._sources[edge.source_id].evidence_ids
        ]
        contradictions = [
            edge for edge in verified if edge.relation == CitationRelation.CONTRADICTS
        ]
        evidence_ids = tuple(
            sorted(
                {
                    evidence_id
                    for edge in verified
                    for evidence_id in edge.evidence_ids
                }
                | {
                    evidence_id
                    for edge in verified
                    for evidence_id in self._sources[edge.source_id].evidence_ids
                }
            )
        )
        if contradictions:
            return ClaimVerification(
                claim_id=claim_id,
                status=ClaimStatus.CONTRADICTED,
                verified_source_ids=tuple(sorted({edge.source_id for edge in verified})),
                independent_publishers=len(
                    {self._sources[edge.source_id].publisher_id for edge in verified}
                ),
                evidence_ids=evidence_ids,
            )

        supporting = [
            edge
            for edge in verified
            if edge.relation == CitationRelation.SUPPORTS
            and self._sources[edge.source_id].trust in {SourceTrust.VERIFIED, SourceTrust.TRUSTED}
        ]
        source_ids = tuple(sorted({edge.source_id for edge in supporting}))
        publishers = {
            self._sources[edge.source_id].publisher_id
            for edge in supporting
        }
        enough_sources = len(source_ids) >= self.policy.minimum_verified_sources
        enough_publishers = len(publishers) >= self.policy.minimum_independent_publishers
        status = (
            ClaimStatus.VERIFIED
            if enough_sources and enough_publishers
            else ClaimStatus.BLOCKED
        )
        return ClaimVerification(
            claim_id=claim_id,
            status=status,
            verified_source_ids=source_ids,
            independent_publishers=len(publishers),
            evidence_ids=evidence_ids,
        )
