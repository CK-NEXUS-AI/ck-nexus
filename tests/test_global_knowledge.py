from creator_app.global_knowledge import (
    Claim,
    CrawlPolicyInput,
    DiscoveryMode,
    Reliability,
    SearchRequest,
    build_discovery_plan,
    evaluate_crawl_policy,
)


def test_claim_requires_provenance() -> None:
    try:
        Claim(
            claim_id="c-1",
            subject="company-a",
            predicate="opened",
            object_value="factory-b",
            source_ids=(),
            confidence=0.8,
            reliability=Reliability.OBSERVED,
            observed_at="2026-09-07T00:00:00Z",
        )
    except ValueError as exc:
        assert "provenance" in str(exc)
    else:
        raise AssertionError("claim without provenance must fail")


def test_crawl_policy_fails_closed_on_unknown_controls() -> None:
    decision = evaluate_crawl_policy(
        CrawlPolicyInput(
            public_resource=True,
            robots_allowed=None,
            terms_allowed=True,
            jurisdiction_allowed=True,
        )
    )
    assert decision.allowed is False
    assert decision.code == "BLOCKED_POLICY"
    assert "robots_unknown" in decision.reasons


def test_discovery_plan_expands_language_region_and_source() -> None:
    plan = build_discovery_plan(
        SearchRequest(
            query="renewable energy investment",
            mode=DiscoveryMode.REACTIVE,
            languages=("th", "en"),
            regions=("asia",),
        )
    )
    assert plan.tasks
    assert {task.language for task in plan.tasks} == {"th", "en"}
    assert {task.region for task in plan.tasks} == {"asia"}
