from creator_app.global_knowledge import (
    CrawlPolicyInput,
    FilterAction,
    FilterCandidate,
    FilterPolicy,
    SourceKind,
    SourceRef,
    evaluate_crawl_policy,
    filter_candidates,
)


def _source(
    source_id: str,
    *,
    content_hash: str,
    language: str = "en",
    source_kind: SourceKind = SourceKind.NEWS,
) -> SourceRef:
    return SourceRef(
        source_id=source_id,
        url=f"https://example.com/{source_id}",
        canonical_url=f"https://example.com/{source_id}",
        source_kind=source_kind,
        language=language,
        region="global",
        observed_at="2026-09-07T00:00:00Z",
        content_hash=content_hash,
    )


def _allowed_policy():
    return evaluate_crawl_policy(
        CrawlPolicyInput(
            public_resource=True,
            robots_allowed=True,
            terms_allowed=True,
            jurisdiction_allowed=True,
        )
    )


def test_filter_rejects_policy_blocked_candidate() -> None:
    blocked = evaluate_crawl_policy(
        CrawlPolicyInput(
            public_resource=True,
            robots_allowed=False,
            terms_allowed=True,
            jurisdiction_allowed=True,
        )
    )
    result = filter_candidates(
        (
            FilterCandidate(
                source=_source("s-1", content_hash="a" * 64),
                policy=blocked,
                content_text="x" * 500,
                extraction_confidence=0.95,
            ),
        )
    )

    assert result.decisions[0].action is FilterAction.REJECT
    assert result.rejected_source_ids == ("s-1",)


def test_filter_rejects_exact_duplicate_and_quarantines_same_lineage() -> None:
    result = filter_candidates(
        (
            FilterCandidate(
                source=_source("s-1", content_hash="a" * 64),
                policy=_allowed_policy(),
                content_text="a" * 500,
                extraction_confidence=0.95,
                lineage_id="wire-1",
            ),
            FilterCandidate(
                source=_source("s-2", content_hash="a" * 64),
                policy=_allowed_policy(),
                content_text="b" * 500,
                extraction_confidence=0.95,
                lineage_id="wire-2",
            ),
            FilterCandidate(
                source=_source("s-3", content_hash="b" * 64),
                policy=_allowed_policy(),
                content_text="c" * 500,
                extraction_confidence=0.95,
                lineage_id="wire-1",
            ),
        ),
        policy=FilterPolicy(min_accepted_sources=1, min_independent_lineages=1),
    )

    assert result.accepted_source_ids == ("s-1",)
    assert result.rejected_source_ids == ("s-2",)
    assert result.quarantined_source_ids == ("s-3",)
    assert result.duplicate_count == 2


def test_filter_expands_search_when_coverage_is_too_narrow() -> None:
    result = filter_candidates(
        (
            FilterCandidate(
                source=_source(
                    "s-1",
                    content_hash="c" * 64,
                    language="en",
                    source_kind=SourceKind.NEWS,
                ),
                policy=_allowed_policy(),
                content_text="reliable extracted content " * 20,
                extraction_confidence=0.9,
                lineage_id="newswire-1",
            ),
        ),
        policy=FilterPolicy(
            min_accepted_sources=3,
            min_independent_lineages=2,
            required_languages=("th", "en"),
            required_source_kinds=(SourceKind.GOVERNMENT, SourceKind.NEWS),
        ),
    )

    assert result.needs_search_expansion is True
    strategies = {item.strategy.value for item in result.expansions}
    assert "alternative_terms" in strategies
    assert "independent_sources" in strategies
    assert "language_coverage" in strategies
    assert "source_diversity" in strategies


def test_filter_never_promotes_candidate_to_verified() -> None:
    result = filter_candidates(
        (
            FilterCandidate(
                source=_source("s-1", content_hash="d" * 64),
                policy=_allowed_policy(),
                content_text="verified-looking text " * 20,
                extraction_confidence=1.0,
            ),
        ),
        policy=FilterPolicy(min_accepted_sources=1, min_independent_lineages=1),
    )

    assert result.decisions[0].reliability.value == "observed"
