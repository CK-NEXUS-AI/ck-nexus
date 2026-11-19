"""Automatic information filtering and search-expansion policy.

This module is deterministic and dependency-light. It classifies discovered
content before knowledge admission and produces machine-readable expansion
directives when evidence is too narrow, duplicated, stale, or low quality.

Filtering never upgrades a claim to VERIFIED and never bypasses crawl policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .contracts import Reliability, SourceKind, SourceRef
from .policy import IngestDecision


class FilterAction(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    QUARANTINE = "quarantine"


class FilterReason(StrEnum):
    ACCEPTED = "accepted"
    POLICY_BLOCKED = "policy_blocked"
    EXACT_DUPLICATE = "exact_duplicate"
    SYNDICATED_DUPLICATE = "syndicated_duplicate"
    CONTENT_TOO_SHORT = "content_too_short"
    EXTRACTION_QUALITY_LOW = "extraction_quality_low"
    STALE_FOR_REQUEST = "stale_for_request"
    PROVENANCE_INCOMPLETE = "provenance_incomplete"


class ExpansionStrategy(StrEnum):
    INDEPENDENT_SOURCES = "independent_sources"
    SOURCE_DIVERSITY = "source_diversity"
    LANGUAGE_COVERAGE = "language_coverage"
    FRESHNESS = "freshness"
    ALTERNATIVE_TERMS = "alternative_terms"
    PRIMARY_SOURCES = "primary_sources"


@dataclass(frozen=True, slots=True)
class FilterCandidate:
    source: SourceRef
    policy: IngestDecision
    content_text: str
    extraction_confidence: float
    lineage_id: str | None = None
    age_seconds: int | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.extraction_confidence <= 1.0:
            raise ValueError("extraction_confidence must be within 0..1")
        if self.age_seconds is not None and self.age_seconds < 0:
            raise ValueError("age_seconds must be non-negative")


@dataclass(frozen=True, slots=True)
class FilterPolicy:
    min_content_chars: int = 120
    min_extraction_confidence: float = 0.55
    max_age_seconds: int | None = None
    min_accepted_sources: int = 3
    min_independent_lineages: int = 2
    required_languages: tuple[str, ...] = ()
    required_source_kinds: tuple[SourceKind, ...] = ()

    def __post_init__(self) -> None:
        if self.min_content_chars < 1:
            raise ValueError("min_content_chars must be positive")
        if not 0.0 <= self.min_extraction_confidence <= 1.0:
            raise ValueError("min_extraction_confidence must be within 0..1")
        if self.max_age_seconds is not None and self.max_age_seconds < 1:
            raise ValueError("max_age_seconds must be positive")
        if self.min_accepted_sources < 1:
            raise ValueError("min_accepted_sources must be positive")
        if self.min_independent_lineages < 1:
            raise ValueError("min_independent_lineages must be positive")


@dataclass(frozen=True, slots=True)
class CandidateDecision:
    source_id: str
    action: FilterAction
    reason: FilterReason
    independent_evidence: bool
    reliability: Reliability


@dataclass(frozen=True, slots=True)
class SearchExpansion:
    strategy: ExpansionStrategy
    reason: str
    target_languages: tuple[str, ...] = ()
    target_source_kinds: tuple[SourceKind, ...] = ()
    query_terms: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FilterBatchResult:
    decisions: tuple[CandidateDecision, ...]
    accepted_source_ids: tuple[str, ...]
    quarantined_source_ids: tuple[str, ...]
    rejected_source_ids: tuple[str, ...]
    independent_lineage_count: int
    duplicate_count: int
    expansions: tuple[SearchExpansion, ...]

    @property
    def needs_search_expansion(self) -> bool:
        return bool(self.expansions)


def filter_candidates(
    candidates: tuple[FilterCandidate, ...],
    *,
    policy: FilterPolicy | None = None,
    known_content_hashes: frozenset[str] = frozenset(),
) -> FilterBatchResult:
    """Filter candidates and emit deterministic search-expansion directives."""

    active_policy = policy or FilterPolicy()
    decisions: list[CandidateDecision] = []
    accepted_ids: list[str] = []
    quarantined_ids: list[str] = []
    rejected_ids: list[str] = []

    seen_hashes = set(known_content_hashes)
    accepted_lineages: set[str] = set()
    accepted_languages: set[str] = set()
    accepted_source_kinds: set[SourceKind] = set()
    duplicate_count = 0
    stale_count = 0

    for candidate in candidates:
        source = candidate.source
        action = FilterAction.ACCEPT
        reason = FilterReason.ACCEPTED
        independent = True

        if not candidate.policy.allowed:
            action = FilterAction.REJECT
            reason = FilterReason.POLICY_BLOCKED
        elif not source.source_id.strip() or not source.content_hash.strip():
            action = FilterAction.REJECT
            reason = FilterReason.PROVENANCE_INCOMPLETE
        elif source.content_hash in seen_hashes:
            action = FilterAction.REJECT
            reason = FilterReason.EXACT_DUPLICATE
            independent = False
            duplicate_count += 1
        elif len(candidate.content_text.strip()) < active_policy.min_content_chars:
            action = FilterAction.QUARANTINE
            reason = FilterReason.CONTENT_TOO_SHORT
        elif candidate.extraction_confidence < active_policy.min_extraction_confidence:
            action = FilterAction.QUARANTINE
            reason = FilterReason.EXTRACTION_QUALITY_LOW
        elif (
            active_policy.max_age_seconds is not None
            and candidate.age_seconds is not None
            and candidate.age_seconds > active_policy.max_age_seconds
        ):
            action = FilterAction.QUARANTINE
            reason = FilterReason.STALE_FOR_REQUEST
            stale_count += 1
        elif candidate.lineage_id and candidate.lineage_id in accepted_lineages:
            action = FilterAction.QUARANTINE
            reason = FilterReason.SYNDICATED_DUPLICATE
            independent = False
            duplicate_count += 1

        decisions.append(
            CandidateDecision(
                source_id=source.source_id,
                action=action,
                reason=reason,
                independent_evidence=independent,
                reliability=Reliability.OBSERVED,
            )
        )

        if action is FilterAction.ACCEPT:
            accepted_ids.append(source.source_id)
            seen_hashes.add(source.content_hash)
            accepted_languages.add(source.language)
            accepted_source_kinds.add(source.source_kind)
            if candidate.lineage_id:
                accepted_lineages.add(candidate.lineage_id)
            else:
                accepted_lineages.add(f"source:{source.source_id}")
        elif action is FilterAction.QUARANTINE:
            quarantined_ids.append(source.source_id)
        else:
            rejected_ids.append(source.source_id)

    expansions = _build_expansions(
        active_policy,
        accepted_count=len(accepted_ids),
        independent_lineage_count=len(accepted_lineages),
        accepted_languages=accepted_languages,
        accepted_source_kinds=accepted_source_kinds,
        duplicate_count=duplicate_count,
        stale_count=stale_count,
    )

    return FilterBatchResult(
        decisions=tuple(decisions),
        accepted_source_ids=tuple(accepted_ids),
        quarantined_source_ids=tuple(quarantined_ids),
        rejected_source_ids=tuple(rejected_ids),
        independent_lineage_count=len(accepted_lineages),
        duplicate_count=duplicate_count,
        expansions=tuple(expansions),
    )


def _build_expansions(
    policy: FilterPolicy,
    *,
    accepted_count: int,
    independent_lineage_count: int,
    accepted_languages: set[str],
    accepted_source_kinds: set[SourceKind],
    duplicate_count: int,
    stale_count: int,
) -> list[SearchExpansion]:
    expansions: list[SearchExpansion] = []

    if accepted_count < policy.min_accepted_sources:
        expansions.append(
            SearchExpansion(
                strategy=ExpansionStrategy.ALTERNATIVE_TERMS,
                reason="accepted_source_count_below_minimum",
                query_terms=("alternative terminology", "related implementation"),
            )
        )

    if independent_lineage_count < policy.min_independent_lineages:
        expansions.append(
            SearchExpansion(
                strategy=ExpansionStrategy.INDEPENDENT_SOURCES,
                reason="independent_evidence_below_minimum",
                query_terms=("independent source", "original reporting"),
            )
        )

    missing_languages = tuple(
        language for language in policy.required_languages if language not in accepted_languages
    )
    if missing_languages:
        expansions.append(
            SearchExpansion(
                strategy=ExpansionStrategy.LANGUAGE_COVERAGE,
                reason="required_language_coverage_missing",
                target_languages=missing_languages,
                query_terms=("original language source",),
            )
        )

    missing_source_kinds = tuple(
        source_kind
        for source_kind in policy.required_source_kinds
        if source_kind not in accepted_source_kinds
    )
    if missing_source_kinds:
        expansions.append(
            SearchExpansion(
                strategy=ExpansionStrategy.SOURCE_DIVERSITY,
                reason="required_source_kind_missing",
                target_source_kinds=missing_source_kinds,
            )
        )

    if duplicate_count:
        expansions.append(
            SearchExpansion(
                strategy=ExpansionStrategy.PRIMARY_SOURCES,
                reason="duplicate_or_syndicated_evidence_detected",
                target_source_kinds=(
                    SourceKind.GOVERNMENT,
                    SourceKind.ACADEMIC,
                    SourceKind.STRUCTURED_DATA,
                    SourceKind.PUBLIC_DOCUMENT,
                ),
                query_terms=("primary source", "official documentation"),
            )
        )

    if stale_count:
        expansions.append(
            SearchExpansion(
                strategy=ExpansionStrategy.FRESHNESS,
                reason="stale_candidates_detected",
                query_terms=("latest", "release notes", "current documentation"),
            )
        )

    return expansions
