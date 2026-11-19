from creator_app.global_knowledge import (
    Claim,
    ClaimObservation,
    ContradictionType,
    GapKind,
    GapSeverity,
    Reliability,
    ResearchCycleAction,
    ResearchRequirements,
    SourceKind,
    SourceObservation,
    SourceRef,
    analyze_coverage,
    analyze_evidence_lineage,
    compile_research_artifact,
    decide_research_cycle,
    detect_contradictions,
)


def _source(
    source_id: str,
    *,
    language: str = "en",
    region: str = "global",
    source_kind: SourceKind = SourceKind.NEWS,
) -> SourceRef:
    return SourceRef(
        source_id=source_id,
        url=f"https://example.test/{source_id}",
        canonical_url=f"https://example.test/{source_id}",
        source_kind=source_kind,
        language=language,
        region=region,
        observed_at="2026-09-07T00:00:00Z",
        content_hash=(source_id * 64)[:64],
    )


def _claim(
    claim_id: str,
    *,
    value: str,
    valid_from: str | None = None,
    valid_to: str | None = None,
) -> Claim:
    return Claim(
        claim_id=claim_id,
        subject="product-a",
        predicate="current_version",
        object_value=value,
        source_ids=(f"source-{claim_id}",),
        confidence=0.9,
        reliability=Reliability.OBSERVED,
        observed_at="2026-09-07T00:00:00Z",
        valid_from=valid_from,
        valid_to=valid_to,
    )


def test_lineage_groups_syndicated_sources_as_one_independent_family() -> None:
    observations = (
        SourceObservation(
            source=_source("a"),
            lineage_id="wire-1",
            is_primary=True,
        ),
        SourceObservation(
            source=_source("b"),
            lineage_id="wire-1",
        ),
        SourceObservation(
            source=_source("c"),
            lineage_id="analysis-2",
            independent_validation=True,
        ),
    )

    report = analyze_evidence_lineage(observations)

    assert report.source_count == 3
    assert report.lineage_count == 2
    assert report.independent_lineage_count == 2
    assert report.validated_lineage_count == 2
    assert report.duplicate_lineages == ("wire-1",)


def test_coverage_is_scoped_to_declared_requirements_not_the_whole_internet() -> None:
    observations = (
        SourceObservation(
            source=_source(
                "a",
                language="en",
                region="us",
                source_kind=SourceKind.GOVERNMENT,
            ),
            lineage_id="official-1",
            is_primary=True,
            age_seconds=60,
            technical_aspects=("api",),
        ),
    )
    requirements = ResearchRequirements(
        min_sources=2,
        min_independent_lineages=2,
        min_primary_sources=1,
        required_languages=("en", "th"),
        required_regions=("us", "th"),
        required_source_kinds=(SourceKind.GOVERNMENT, SourceKind.ACADEMIC),
        required_technical_aspects=("api", "security"),
        max_age_seconds=3600,
    )

    report = analyze_coverage(observations, requirements)

    assert report.source_coverage == 0.5
    assert report.language_coverage == 0.5
    assert report.region_coverage == 0.5
    assert report.source_kind_coverage == 0.5
    assert report.technical_coverage == 0.5
    assert report.freshness_coverage == 1.0
    assert report.missing_languages == ("th",)
    assert report.missing_technical_aspects == ("security",)


def test_unspecified_coverage_dimension_is_not_claimed_complete() -> None:
    report = analyze_coverage(
        (
            SourceObservation(
                source=_source("a"),
                lineage_id="lineage-1",
                is_primary=True,
            ),
        ),
        ResearchRequirements(
            min_sources=1,
            min_independent_lineages=1,
            min_primary_sources=1,
        ),
    )

    assert report.language_coverage is None
    assert report.region_coverage is None
    assert report.source_kind_coverage is None
    assert report.technical_coverage is None


def test_contradiction_detection_requires_explicit_exclusive_predicate() -> None:
    claims = (
        ClaimObservation(_claim("a", value="1.0")),
        ClaimObservation(_claim("b", value="2.0")),
    )

    assert detect_contradictions(claims) == ()

    contradictions = detect_contradictions(
        claims,
        exclusive_predicates=frozenset({"current_version"}),
    )

    assert len(contradictions) == 1
    assert contradictions[0].contradiction_type is ContradictionType.FACTUAL
    assert contradictions[0].values == ("1.0", "2.0")


def test_temporally_disjoint_values_are_not_treated_as_factual_conflict() -> None:
    claims = (
        ClaimObservation(
            _claim(
                "a",
                value="1.0",
                valid_from="2025-01-01T00:00:00Z",
                valid_to="2025-12-31T23:59:59Z",
            )
        ),
        ClaimObservation(
            _claim(
                "b",
                value="2.0",
                valid_from="2026-01-01T00:00:00Z",
            )
        ),
    )

    contradictions = detect_contradictions(
        claims,
        exclusive_predicates=frozenset({"current_version"}),
    )

    assert contradictions == ()


def test_compiler_detects_gaps_and_emits_expansion_without_verifying() -> None:
    observations = (
        SourceObservation(
            source=_source("a", language="en", source_kind=SourceKind.NEWS),
            lineage_id="wire-1",
            age_seconds=9999,
        ),
    )
    requirements = ResearchRequirements(
        min_sources=3,
        min_independent_lineages=2,
        min_primary_sources=1,
        required_languages=("en", "th"),
        required_source_kinds=(SourceKind.GOVERNMENT, SourceKind.NEWS),
        max_age_seconds=3600,
    )

    artifact = compile_research_artifact(
        observations,
        (),
        requirements,
    )

    kinds = {gap.kind for gap in artifact.gaps}
    assert GapKind.WEAK in kinds
    assert GapKind.STALE in kinds
    assert GapKind.COVERAGE in kinds
    assert artifact.expansions
    assert artifact.ready_for_analysis is False
    assert artifact.verified is False


def test_missing_sources_is_critical_and_requests_more_research() -> None:
    artifact = compile_research_artifact(
        (),
        (),
        ResearchRequirements(),
    )

    assert artifact.gaps[0].kind is GapKind.MISSING
    assert artifact.gaps[0].severity is GapSeverity.CRITICAL
    decision = decide_research_cycle(artifact)
    assert decision.action is ResearchCycleAction.CONTINUE_RESEARCH


def test_unresolved_contradiction_after_exhaustion_routes_to_human_review() -> None:
    observations = (
        SourceObservation(
            source=_source(
                "a",
                source_kind=SourceKind.GOVERNMENT,
            ),
            lineage_id="official-1",
            is_primary=True,
        ),
        SourceObservation(
            source=_source(
                "b",
                source_kind=SourceKind.ACADEMIC,
            ),
            lineage_id="academic-1",
            independent_validation=True,
        ),
    )
    claims = (
        ClaimObservation(_claim("a", value="1.0")),
        ClaimObservation(_claim("b", value="2.0")),
    )
    artifact = compile_research_artifact(
        observations,
        claims,
        ResearchRequirements(
            min_sources=2,
            min_independent_lineages=2,
            min_primary_sources=1,
        ),
        exclusive_predicates=frozenset({"current_version"}),
    )

    decision = decide_research_cycle(
        artifact,
        research_exhausted=True,
    )

    assert decision.action is ResearchCycleAction.HUMAN_REVIEW_REQUIRED


def test_satisfied_declared_requirements_can_enter_analysis_but_not_verified() -> None:
    observations = (
        SourceObservation(
            source=_source(
                "a",
                language="en",
                region="global",
                source_kind=SourceKind.GOVERNMENT,
            ),
            lineage_id="official-1",
            is_primary=True,
            technical_aspects=("api",),
        ),
        SourceObservation(
            source=_source(
                "b",
                language="th",
                region="asia",
                source_kind=SourceKind.ACADEMIC,
            ),
            lineage_id="academic-1",
            independent_validation=True,
            technical_aspects=("security",),
        ),
    )
    artifact = compile_research_artifact(
        observations,
        (),
        ResearchRequirements(
            min_sources=2,
            min_independent_lineages=2,
            min_primary_sources=1,
            required_languages=("en", "th"),
            required_source_kinds=(SourceKind.GOVERNMENT, SourceKind.ACADEMIC),
            required_technical_aspects=("api", "security"),
        ),
    )

    assert artifact.gaps == ()
    assert artifact.ready_for_analysis is True
    assert artifact.verified is False
    assert decide_research_cycle(artifact).action is ResearchCycleAction.READY_FOR_ANALYSIS
