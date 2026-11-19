"""Semantic content intelligence for Pinterest/image-derived CK-NEXUS research."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum

from .contracts import CandidateDecision, ClaimKind


class ContentEvidenceState(StrEnum):
    DISCOVERED = "discovered"
    CONTENT_EXTRACTED = "content_extracted"
    NORMALIZED = "normalized"
    DEDUPED = "deduped"
    RESEARCHED = "researched"
    VERIFIED_OR_REVIEWED = "verified_or_reviewed"
    CK_NEXUS_MAPPED = "ck_nexus_mapped"
    DEVELOPMENT_CANDIDATE = "development_candidate"


@dataclass(frozen=True, slots=True)
class ContentClaim:
    text: str
    kind: ClaimKind
    source_id: str
    confidence: float = 1.0
    requires_external_verification: bool = True
    vendor_or_entity: str = ""
    numeric_claim: bool = False
    freshness_sensitive: bool = False

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("claim text must not be empty")
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class ContentRecord:
    source_id: str
    source_url: str
    title: str = ""
    description: str = ""
    publisher: str = ""
    published_at: str = ""
    visible_text_verbatim: str = ""
    headings: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    entities: tuple[str, ...] = ()
    architecture_patterns: tuple[str, ...] = ()
    workflow_steps: tuple[str, ...] = ()
    concepts: tuple[str, ...] = ()
    claims: tuple[ContentClaim, ...] = ()
    evidence_state: ContentEvidenceState = ContentEvidenceState.DISCOVERED
    provenance_digest: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        if not self.source_url.strip():
            raise ValueError("source_url must not be empty")
        if self.provenance_digest is not None:
            value = self.provenance_digest
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value
            ):
                raise ValueError("provenance_digest must be lowercase SHA-256 hex")
        for claim in self.claims:
            if claim.source_id != self.source_id:
                raise ValueError("claim source_id does not match content record")


@dataclass(frozen=True, slots=True)
class ResearchQuery:
    query: str
    source_id: str
    purpose: str = "official_source_research"

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("research query must not be empty")
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")


@dataclass(frozen=True, slots=True)
class CapabilityGap:
    gap_id: str
    title: str
    source_ids: tuple[str, ...]
    decision: CandidateDecision
    existing_capability_refs: tuple[str, ...] = ()
    evidence_needed: tuple[str, ...] = ()
    priority: str = "P2"
    benchmark_required: bool = True
    security_review_required: bool = True
    human_review_required: bool = True
    production_effect: bool = False

    def __post_init__(self) -> None:
        if not self.gap_id.strip() or not self.title.strip():
            raise ValueError("gap id and title must not be empty")
        if not self.source_ids:
            raise ValueError("source_ids must not be empty")
        if self.priority not in {"P0", "P1", "P2", "P3"}:
            raise ValueError("priority must be P0, P1, P2, or P3")
        if self.production_effect:
            raise ValueError("content-derived gaps cannot affect production")


class ContentIntelligencePipeline:
    """Turn semantic source content into research queries and gated capability gaps."""

    _VERIFY_KINDS = {
        ClaimKind.FACT,
        ClaimKind.PRIVACY,
        ClaimKind.PRICING,
        ClaimKind.METRIC,
        ClaimKind.PRODUCT,
    }

    @staticmethod
    def _clean(value: str) -> str:
        return " ".join(value.split()).strip()

    def research_queries(
        self,
        record: ContentRecord,
        *,
        max_queries: int = 32,
    ) -> tuple[ResearchQuery, ...]:
        if max_queries < 1 or max_queries > 100:
            raise ValueError("max_queries must be between 1 and 100")

        raw: list[tuple[str, str]] = []
        title = self._clean(record.title)
        description = self._clean(record.description)

        if title:
            raw.append((title, "source_title"))
        if title and description:
            raw.append((f"{title} {description}", "source_title_description"))

        for heading in record.headings:
            value = self._clean(heading)
            if value:
                raw.append((value, "visible_heading"))

        for entity in record.entities:
            value = self._clean(entity)
            if value:
                raw.append((value, "named_entity"))
                if title:
                    raw.append((f"{value} {title}", "entity_context"))

        for keyword in record.keywords:
            value = self._clean(keyword)
            if value:
                raw.append((value, "keyword"))

        for pattern in record.architecture_patterns:
            value = self._clean(pattern)
            if value:
                raw.append((f"{value} architecture", "architecture_research"))

        for concept in record.concepts:
            value = self._clean(concept)
            if value:
                raw.append((value, "concept_research"))

        for claim in record.claims:
            raw.append((self._clean(claim.text), "claim_verification"))

        seen: set[str] = set()
        queries: list[ResearchQuery] = []
        for query, purpose in raw:
            query = self._clean(query)[:512]
            key = query.casefold()
            if not query or key in seen:
                continue
            seen.add(key)
            queries.append(
                ResearchQuery(
                    query=query,
                    source_id=record.source_id,
                    purpose=purpose,
                )
            )
            if len(queries) >= max_queries:
                break
        return tuple(queries)

    def decision_for_claim(
        self,
        claim: ContentClaim,
        *,
        duplicate_found: bool = False,
        reusable_existing_capability: bool = False,
    ) -> CandidateDecision:
        if reusable_existing_capability:
            return CandidateDecision.REUSE
        if duplicate_found:
            return CandidateDecision.DUPLICATE
        if claim.requires_external_verification:
            return CandidateDecision.VERIFY
        if claim.kind in self._VERIFY_KINDS:
            return CandidateDecision.VERIFY
        if claim.numeric_claim or claim.vendor_or_entity or claim.freshness_sensitive:
            return CandidateDecision.VERIFY
        if claim.kind in {ClaimKind.WORKFLOW, ClaimKind.PROMPT_PATTERN}:
            return CandidateDecision.BENCHMARK
        if claim.kind == ClaimKind.CAPABILITY:
            return CandidateDecision.DEV_CANDIDATE
        return CandidateDecision.BENCHMARK

    def gap_from_claim(
        self,
        record: ContentRecord,
        claim: ContentClaim,
        *,
        duplicate_found: bool = False,
        reusable_existing_capability: bool = False,
        existing_capability_refs: tuple[str, ...] = (),
        priority: str = "P2",
    ) -> CapabilityGap:
        if claim.source_id != record.source_id:
            raise ValueError("claim source_id does not match content record")

        decision = self.decision_for_claim(
            claim,
            duplicate_found=duplicate_found,
            reusable_existing_capability=reusable_existing_capability,
        )

        evidence: list[str] = ["source_ref", "content_digest"]
        if decision == CandidateDecision.VERIFY:
            evidence.extend(("official_source", "checked_at", "verification_result"))
        if decision in {
            CandidateDecision.BENCHMARK,
            CandidateDecision.DEV_CANDIDATE,
        }:
            evidence.extend(("canonical_baseline", "delta", "benchmark_result"))
        evidence.extend(("security_review", "independent_verification"))

        material = "|".join(
            (record.source_id, claim.kind.value, self._clean(claim.text))
        ).encode("utf-8")
        gap_id = "ctgap-" + hashlib.sha256(material).hexdigest()[:20]

        return CapabilityGap(
            gap_id=gap_id,
            title=self._clean(claim.text)[:160],
            source_ids=(record.source_id,),
            decision=decision,
            existing_capability_refs=existing_capability_refs,
            evidence_needed=tuple(dict.fromkeys(evidence)),
            priority=priority,
            benchmark_required=decision
            not in {CandidateDecision.REUSE, CandidateDecision.DUPLICATE},
            security_review_required=True,
            human_review_required=True,
            production_effect=False,
        )
