"""Knowledge-driven research analysis for CK-NEXUS.

The module consumes already-admitted observations and produces deterministic
coverage, evidence-lineage, contradiction, diversity, and knowledge-gap
signals. It does not perform network access and does not promote information
to VERIFIED.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .contracts import Claim, SourceKind, SourceRef
from .filtering import ExpansionStrategy, SearchExpansion


class GapKind(StrEnum):
    MISSING = "missing"
    WEAK = "weak"
    CONTRADICTION = "contradiction"
    STALE = "stale"
    COVERAGE = "coverage"


class GapSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContradictionType(StrEnum):
    FACTUAL = "factual"
    TEMPORAL = "temporal"
    LOGICAL_REVIEW_REQUIRED = "logical_review_required"


class ResearchCycleAction(StrEnum):
    CONTINUE_RESEARCH = "continue_research"
    READY_FOR_ANALYSIS = "ready_for_analysis"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


@dataclass(frozen=True, slots=True)
class ResearchRequirements:
    min_sources: int = 3
    min_independent_lineages: int = 2
    min_primary_sources: int = 1
    required_languages: tuple[str, ...] = ()
    required_regions: tuple[str, ...] = ()
    required_source_kinds: tuple[SourceKind, ...] = ()
    required_technical_aspects: tuple[str, ...] = ()
    max_age_seconds: int | None = None

    def __post_init__(self) -> None:
        if self.min_sources < 1:
            raise ValueError("min_sources must be positive")
        if self.min_independent_lineages < 1:
            raise ValueError("min_independent_lineages must be positive")
        if self.min_primary_sources < 0:
            raise ValueError("min_primary_sources must be non-negative")
        if self.max_age_seconds is not None and self.max_age_seconds < 1:
            raise ValueError("max_age_seconds must be positive")


@dataclass(frozen=True, slots=True)
class SourceObservation:
    source: SourceRef
    lineage_id: str
    is_primary: bool = False
    independent_validation: bool = False
    age_seconds: int | None = None
    technical_aspects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.lineage_id.strip():
            raise ValueError("lineage_id is required")
        if self.age_seconds is not None and self.age_seconds < 0:
            raise ValueError("age_seconds must be non-negative")


@dataclass(frozen=True, slots=True)
class EvidenceLineageReport:
    source_count: int
    lineage_count: int
    independent_lineage_count: int
    validated_lineage_count: int
    duplicate_lineages: tuple[str, ...]
    source_lineage_pairs: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class CoverageReport:
    source_coverage: float
    lineage_coverage: float
    primary_source_coverage: float
    language_coverage: float | None
    region_coverage: float | None
    source_kind_coverage: float | None
    technical_coverage: float | None
    freshness_coverage: float | None
    overall_scoped_coverage: float
    missing_languages: tuple[str, ...] = ()
    missing_regions: tuple[str, ...] = ()
    missing_source_kinds: tuple[SourceKind, ...] = ()
    missing_technical_aspects: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceDiversityReport:
    unique_languages: int
    unique_regions: int
    unique_source_kinds: int
    independent_lineages: int
    primary_sources: int
    declared_requirement_score: float


@dataclass(frozen=True, slots=True)
class ClaimObservation:
    claim: Claim
    scope: str = "default"


@dataclass(frozen=True, slots=True)
class ContradictionRecord:
    contradiction_type: ContradictionType
    claim_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    subject: str
    predicate: str
    values: tuple[str, ...]
    reason: str
    confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within 0..1")


@dataclass(frozen=True, slots=True)
class KnowledgeGap:
    kind: GapKind
    severity: GapSeverity
    reason: str
    resolvable_by_research: bool
    expansion_strategies: tuple[ExpansionStrategy, ...] = ()


@dataclass(frozen=True, slots=True)
class ResearchCompilationArtifact:
    source_ids: tuple[str, ...]
    claim_ids: tuple[str, ...]
    lineage: EvidenceLineageReport
    coverage: CoverageReport
    diversity: SourceDiversityReport
    contradictions: tuple[ContradictionRecord, ...]
    gaps: tuple[KnowledgeGap, ...]
    expansions: tuple[SearchExpansion, ...]
    ready_for_analysis: bool
    verified: bool = False


@dataclass(frozen=True, slots=True)
class ResearchCycleDecision:
    action: ResearchCycleAction
    reasons: tuple[str, ...]


def analyze_evidence_lineage(
    observations: tuple[SourceObservation, ...],
) -> EvidenceLineageReport:
    lineage_members: dict[str, list[SourceObservation]] = {}
    pairs: list[tuple[str, str]] = []

    for observation in observations:
        lineage_members.setdefault(observation.lineage_id, []).append(observation)
        pairs.append((observation.source.source_id, observation.lineage_id))

    duplicate_lineages = tuple(
        sorted(
            lineage_id
            for lineage_id, members in lineage_members.items()
            if len(members) > 1
        )
    )

    validated_lineages = sum(
        1
        for members in lineage_members.values()
        if any(item.is_primary or item.independent_validation for item in members)
    )

    return EvidenceLineageReport(
        source_count=len(observations),
        lineage_count=len(lineage_members),
        independent_lineage_count=len(lineage_members),
        validated_lineage_count=validated_lineages,
        duplicate_lineages=duplicate_lineages,
        source_lineage_pairs=tuple(sorted(pairs)),
    )


def analyze_coverage(
    observations: tuple[SourceObservation, ...],
    requirements: ResearchRequirements,
    lineage: EvidenceLineageReport | None = None,
) -> CoverageReport:
    lineage_report = lineage or analyze_evidence_lineage(observations)
    languages = {item.source.language for item in observations}
    regions = {item.source.region for item in observations}
    source_kinds = {item.source.source_kind for item in observations}
    technical_aspects = {
        aspect
        for item in observations
        for aspect in item.technical_aspects
    }
    primary_count = sum(1 for item in observations if item.is_primary)

    source_coverage = min(1.0, len(observations) / requirements.min_sources)
    lineage_coverage = min(
        1.0,
        lineage_report.independent_lineage_count
        / requirements.min_independent_lineages,
    )
    primary_coverage = (
        1.0
        if requirements.min_primary_sources == 0
        else min(1.0, primary_count / requirements.min_primary_sources)
    )

    language_coverage, missing_languages = _set_coverage(
        languages,
        requirements.required_languages,
    )
    region_coverage, missing_regions = _set_coverage(
        regions,
        requirements.required_regions,
    )
    source_kind_coverage, missing_source_kinds = _set_coverage(
        source_kinds,
        requirements.required_source_kinds,
    )
    technical_coverage, missing_technical = _set_coverage(
        technical_aspects,
        requirements.required_technical_aspects,
    )

    freshness_coverage: float | None = None
    if requirements.max_age_seconds is not None:
        if not observations:
            freshness_coverage = 0.0
        else:
            fresh = sum(
                1
                for item in observations
                if item.age_seconds is not None
                and item.age_seconds <= requirements.max_age_seconds
            )
            freshness_coverage = fresh / len(observations)

    scoped_scores = [
        source_coverage,
        lineage_coverage,
        primary_coverage,
    ]
    scoped_scores.extend(
        score
        for score in (
            language_coverage,
            region_coverage,
            source_kind_coverage,
            technical_coverage,
            freshness_coverage,
        )
        if score is not None
    )

    return CoverageReport(
        source_coverage=source_coverage,
        lineage_coverage=lineage_coverage,
        primary_source_coverage=primary_coverage,
        language_coverage=language_coverage,
        region_coverage=region_coverage,
        source_kind_coverage=source_kind_coverage,
        technical_coverage=technical_coverage,
        freshness_coverage=freshness_coverage,
        overall_scoped_coverage=sum(scoped_scores) / len(scoped_scores),
        missing_languages=tuple(str(item) for item in missing_languages),
        missing_regions=tuple(str(item) for item in missing_regions),
        missing_source_kinds=tuple(missing_source_kinds),
        missing_technical_aspects=tuple(str(item) for item in missing_technical),
    )


def analyze_source_diversity(
    observations: tuple[SourceObservation, ...],
    requirements: ResearchRequirements,
    coverage: CoverageReport | None = None,
    lineage: EvidenceLineageReport | None = None,
) -> SourceDiversityReport:
    coverage_report = coverage or analyze_coverage(observations, requirements, lineage)
    lineage_report = lineage or analyze_evidence_lineage(observations)

    return SourceDiversityReport(
        unique_languages=len({item.source.language for item in observations}),
        unique_regions=len({item.source.region for item in observations}),
        unique_source_kinds=len({item.source.source_kind for item in observations}),
        independent_lineages=lineage_report.independent_lineage_count,
        primary_sources=sum(1 for item in observations if item.is_primary),
        declared_requirement_score=coverage_report.overall_scoped_coverage,
    )


def detect_contradictions(
    claims: tuple[ClaimObservation, ...],
    *,
    exclusive_predicates: frozenset[str] = frozenset(),
) -> tuple[ContradictionRecord, ...]:
    """Detect deterministic conflicts only for explicitly exclusive predicates.

    Semantic or logical contradictions that require interpretation are not
    guessed here. They should be routed to an independent review adapter.
    """

    grouped: dict[tuple[str, str, str], list[Claim]] = {}
    for observation in claims:
        claim = observation.claim
        if claim.predicate not in exclusive_predicates:
            continue
        key = (claim.subject, claim.predicate, observation.scope)
        grouped.setdefault(key, []).append(claim)

    records: list[ContradictionRecord] = []
    for (subject, predicate, _scope), members in grouped.items():
        active = [
            claim
            for claim in members
            if not _is_time_disjoint_from_all(claim, members)
        ]
        values = tuple(sorted({claim.object_value for claim in active}))
        if len(values) < 2:
            continue

        source_ids = tuple(
            sorted({source_id for claim in active for source_id in claim.source_ids})
        )
        records.append(
            ContradictionRecord(
                contradiction_type=ContradictionType.FACTUAL,
                claim_ids=tuple(sorted(claim.claim_id for claim in active)),
                source_ids=source_ids,
                subject=subject,
                predicate=predicate,
                values=values,
                reason="exclusive_predicate_has_multiple_overlapping_values",
                confidence=1.0,
            )
        )

    return tuple(records)


def detect_knowledge_gaps(
    observations: tuple[SourceObservation, ...],
    requirements: ResearchRequirements,
    *,
    coverage: CoverageReport | None = None,
    lineage: EvidenceLineageReport | None = None,
    contradictions: tuple[ContradictionRecord, ...] = (),
) -> tuple[KnowledgeGap, ...]:
    coverage_report = coverage or analyze_coverage(observations, requirements, lineage)
    lineage_report = lineage or analyze_evidence_lineage(observations)
    gaps: list[KnowledgeGap] = []

    if not observations:
        gaps.append(
            KnowledgeGap(
                kind=GapKind.MISSING,
                severity=GapSeverity.CRITICAL,
                reason="no_admitted_sources",
                resolvable_by_research=True,
                expansion_strategies=(
                    ExpansionStrategy.ALTERNATIVE_TERMS,
                    ExpansionStrategy.PRIMARY_SOURCES,
                ),
            )
        )
        return tuple(gaps)

    if len(observations) < requirements.min_sources:
        gaps.append(
            KnowledgeGap(
                kind=GapKind.WEAK,
                severity=GapSeverity.HIGH,
                reason="source_count_below_declared_minimum",
                resolvable_by_research=True,
                expansion_strategies=(ExpansionStrategy.ALTERNATIVE_TERMS,),
            )
        )

    if (
        lineage_report.independent_lineage_count
        < requirements.min_independent_lineages
    ):
        gaps.append(
            KnowledgeGap(
                kind=GapKind.WEAK,
                severity=GapSeverity.HIGH,
                reason="independent_evidence_below_declared_minimum",
                resolvable_by_research=True,
                expansion_strategies=(
                    ExpansionStrategy.INDEPENDENT_SOURCES,
                    ExpansionStrategy.PRIMARY_SOURCES,
                ),
            )
        )

    if contradictions:
        gaps.append(
            KnowledgeGap(
                kind=GapKind.CONTRADICTION,
                severity=GapSeverity.HIGH,
                reason="unresolved_contradictions",
                resolvable_by_research=True,
                expansion_strategies=(
                    ExpansionStrategy.INDEPENDENT_SOURCES,
                    ExpansionStrategy.PRIMARY_SOURCES,
                ),
            )
        )

    if (
        coverage_report.freshness_coverage is not None
        and coverage_report.freshness_coverage < 1.0
    ):
        gaps.append(
            KnowledgeGap(
                kind=GapKind.STALE,
                severity=GapSeverity.MEDIUM,
                reason="stale_or_undated_sources_present",
                resolvable_by_research=True,
                expansion_strategies=(ExpansionStrategy.FRESHNESS,),
            )
        )

    coverage_reasons: list[str] = []
    if coverage_report.missing_languages:
        coverage_reasons.append("language")
    if coverage_report.missing_regions:
        coverage_reasons.append("region")
    if coverage_report.missing_source_kinds:
        coverage_reasons.append("source_kind")
    if coverage_report.missing_technical_aspects:
        coverage_reasons.append("technical")

    if coverage_reasons:
        gaps.append(
            KnowledgeGap(
                kind=GapKind.COVERAGE,
                severity=GapSeverity.MEDIUM,
                reason="missing_declared_coverage:" + ",".join(coverage_reasons),
                resolvable_by_research=True,
                expansion_strategies=(
                    ExpansionStrategy.SOURCE_DIVERSITY,
                    ExpansionStrategy.LANGUAGE_COVERAGE,
                ),
            )
        )

    return tuple(gaps)


def build_search_expansions(
    gaps: tuple[KnowledgeGap, ...],
    coverage: CoverageReport,
) -> tuple[SearchExpansion, ...]:
    expansions: list[SearchExpansion] = []
    emitted: set[tuple[str, str]] = set()

    for gap in gaps:
        for strategy in gap.expansion_strategies:
            key = (strategy.value, gap.reason)
            if key in emitted:
                continue
            emitted.add(key)

            target_languages: tuple[str, ...] = ()
            target_source_kinds: tuple[SourceKind, ...] = ()
            query_terms: tuple[str, ...] = ()

            if strategy is ExpansionStrategy.LANGUAGE_COVERAGE:
                target_languages = coverage.missing_languages
            elif strategy is ExpansionStrategy.SOURCE_DIVERSITY:
                target_source_kinds = coverage.missing_source_kinds
            elif strategy is ExpansionStrategy.PRIMARY_SOURCES:
                query_terms = ("official", "primary source", "original publication")
            elif strategy is ExpansionStrategy.INDEPENDENT_SOURCES:
                query_terms = ("independent verification", "independent analysis")
            elif strategy is ExpansionStrategy.FRESHNESS:
                query_terms = ("latest", "current", "release notes")
            elif strategy is ExpansionStrategy.ALTERNATIVE_TERMS:
                query_terms = ("alternative terminology", "related approach")

            expansions.append(
                SearchExpansion(
                    strategy=strategy,
                    reason=gap.reason,
                    target_languages=target_languages,
                    target_source_kinds=target_source_kinds,
                    query_terms=query_terms,
                )
            )

    return tuple(expansions)


def compile_research_artifact(
    observations: tuple[SourceObservation, ...],
    claims: tuple[ClaimObservation, ...],
    requirements: ResearchRequirements,
    *,
    exclusive_predicates: frozenset[str] = frozenset(),
) -> ResearchCompilationArtifact:
    lineage = analyze_evidence_lineage(observations)
    coverage = analyze_coverage(observations, requirements, lineage)
    diversity = analyze_source_diversity(
        observations,
        requirements,
        coverage,
        lineage,
    )
    contradictions = detect_contradictions(
        claims,
        exclusive_predicates=exclusive_predicates,
    )
    gaps = detect_knowledge_gaps(
        observations,
        requirements,
        coverage=coverage,
        lineage=lineage,
        contradictions=contradictions,
    )
    expansions = build_search_expansions(gaps, coverage)

    blocking_gap = any(
        gap.severity in {GapSeverity.HIGH, GapSeverity.CRITICAL}
        for gap in gaps
    )

    return ResearchCompilationArtifact(
        source_ids=tuple(item.source.source_id for item in observations),
        claim_ids=tuple(item.claim.claim_id for item in claims),
        lineage=lineage,
        coverage=coverage,
        diversity=diversity,
        contradictions=contradictions,
        gaps=gaps,
        expansions=expansions,
        ready_for_analysis=not blocking_gap and not contradictions,
        verified=False,
    )


def decide_research_cycle(
    artifact: ResearchCompilationArtifact,
    *,
    research_exhausted: bool = False,
) -> ResearchCycleDecision:
    if artifact.contradictions and research_exhausted:
        return ResearchCycleDecision(
            action=ResearchCycleAction.HUMAN_REVIEW_REQUIRED,
            reasons=("contradictions_remain_after_research_exhaustion",),
        )

    if artifact.gaps or artifact.expansions:
        return ResearchCycleDecision(
            action=ResearchCycleAction.CONTINUE_RESEARCH,
            reasons=tuple(gap.reason for gap in artifact.gaps),
        )

    return ResearchCycleDecision(
        action=ResearchCycleAction.READY_FOR_ANALYSIS,
        reasons=("declared_research_requirements_satisfied",),
    )


def _set_coverage(
    observed: set[object],
    required: tuple[object, ...],
) -> tuple[float | None, tuple[object, ...]]:
    if not required:
        return None, ()
    missing = tuple(item for item in required if item not in observed)
    matched = len(required) - len(missing)
    return matched / len(required), missing


def _is_time_disjoint_from_all(claim: Claim, members: list[Claim]) -> bool:
    comparable = [
        other
        for other in members
        if other.claim_id != claim.claim_id
        and other.object_value != claim.object_value
    ]
    if not comparable:
        return False

    return all(_time_ranges_disjoint(claim, other) for other in comparable)


def _time_ranges_disjoint(left: Claim, right: Claim) -> bool:
    if left.valid_from is None or right.valid_from is None:
        return False
    if left.valid_to is not None and left.valid_to < right.valid_from:
        return True
    if right.valid_to is not None and right.valid_to < left.valid_from:
        return True
    return False
