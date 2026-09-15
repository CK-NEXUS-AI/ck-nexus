from urllib.parse import parse_qs, urlsplit

from creator_app.global_knowledge import (
    Claim,
    ClaimObservation,
    CrawlPolicyInput,
    EvidenceEdgeKind,
    EvidenceGraph,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    EvidenceNodeKind,
    Reliability,
    ResearchCycleAction,
    ResearchRequirements,
    SourceKind,
    SourceObservation,
    SourceRef,
    build_research_routing_plan,
    compile_research_artifact,
)
from creator_app.global_knowledge.connectors import (
    Crawl4AIAdapter,
    CrawlRequest,
    CrawlStatus,
    SearxngConfig,
    SearxngDiscoveryAdapter,
    SearxngStatus,
)


def _source(source_id: str, *, kind: SourceKind = SourceKind.NEWS) -> SourceRef:
    return SourceRef(
        source_id=source_id,
        url=f"https://example.test/{source_id}",
        canonical_url=f"https://example.test/{source_id}",
        source_kind=kind,
        language="en",
        region="global",
        observed_at="2026-09-07T00:00:00Z",
        content_hash=(source_id * 64)[:64],
    )


async def test_searxng_adapter_builds_json_query_and_bounds_results() -> None:
    observed_url = ""

    async def fake_fetch(url: str):
        nonlocal observed_url
        observed_url = url
        return {
            "results": [
                {
                    "url": "https://docs.example/a",
                    "title": "A",
                    "content": "first",
                    "engine": "docs",
                    "score": 1.0,
                },
                {
                    "url": "https://docs.example/b",
                    "title": "B",
                    "content": "second",
                },
            ]
        }

    adapter = SearxngDiscoveryAdapter(
        SearxngConfig(
            base_url="http://127.0.0.1:8080",
            max_results=1,
        ),
        fetch_json=fake_fetch,
    )

    result = await adapter.search(
        "knowledge graph",
        language="en",
        categories=("general", "it"),
        time_range="month",
    )

    params = parse_qs(urlsplit(observed_url).query)
    assert result.status is SearxngStatus.SUCCESS
    assert len(result.hits) == 1
    assert params["q"] == ["knowledge graph"]
    assert params["format"] == ["json"]
    assert params["language"] == ["en"]
    assert params["categories"] == ["general,it"]
    assert params["time_range"] == ["month"]


async def test_searxng_adapter_fails_closed_on_invalid_response() -> None:
    adapter = SearxngDiscoveryAdapter(
        SearxngConfig(base_url="https://search.example"),
        fetch_json=lambda _url: {"unexpected": []},
    )

    result = await adapter.search("test")

    assert result.status is SearxngStatus.INVALID_RESPONSE
    assert result.hits == ()


async def test_crawl4ai_policy_block_prevents_provider_execution() -> None:
    called = False

    async def fake_runner(_url: str):
        nonlocal called
        called = True
        return {"success": True, "markdown": "should not run"}

    adapter = Crawl4AIAdapter(runner=fake_runner)
    result = await adapter.crawl(
        CrawlRequest("https://example.test/page"),
        CrawlPolicyInput(
            public_resource=True,
            robots_allowed=False,
            terms_allowed=True,
            jurisdiction_allowed=True,
        ),
    )

    assert result.status is CrawlStatus.BLOCKED_POLICY
    assert called is False


async def test_crawl4ai_rejects_private_literal_target() -> None:
    adapter = Crawl4AIAdapter(
        runner=lambda _url: {"success": True, "markdown": "unused"}
    )

    result = await adapter.crawl(
        CrawlRequest("http://127.0.0.1/private"),
        CrawlPolicyInput(
            public_resource=True,
            robots_allowed=True,
            terms_allowed=True,
            jurisdiction_allowed=True,
        ),
    )

    assert result.status is CrawlStatus.INVALID_URL


async def test_crawl4ai_bounds_content_and_hashes_admitted_output() -> None:
    adapter = Crawl4AIAdapter(
        runner=lambda _url: {
            "success": True,
            "markdown": "abcdefghij",
            "final_url": "https://example.test/final",
        }
    )

    result = await adapter.crawl(
        CrawlRequest(
            "https://example.test/start",
            max_content_chars=5,
        ),
        CrawlPolicyInput(
            public_resource=True,
            robots_allowed=True,
            terms_allowed=True,
            jurisdiction_allowed=True,
        ),
    )

    assert result.status is CrawlStatus.SUCCESS
    assert result.markdown == "abcde"
    assert result.truncated is True
    assert result.content_hash is not None
    assert len(result.content_hash) == 64


def test_evidence_graph_traces_lineage_and_independent_validation() -> None:
    graph = EvidenceGraph(
        nodes=(
            EvidenceGraphNode(
                node_id="source-a",
                kind=EvidenceNodeKind.SOURCE,
                source_id="a",
                observed_at="2026-09-07T00:00:00Z",
            ),
            EvidenceGraphNode(
                node_id="source-b",
                kind=EvidenceNodeKind.SOURCE,
                source_id="b",
                observed_at="2026-09-07T00:00:00Z",
            ),
            EvidenceGraphNode(
                node_id="claim-c",
                kind=EvidenceNodeKind.CLAIM,
                claim_id="c",
                observed_at="2026-09-07T00:00:00Z",
            ),
        ),
        edges=(
            EvidenceGraphEdge(
                edge_id="e1",
                from_node_id="source-b",
                to_node_id="source-a",
                kind=EvidenceEdgeKind.CITES,
            ),
            EvidenceGraphEdge(
                edge_id="e2",
                from_node_id="claim-c",
                to_node_id="source-b",
                kind=EvidenceEdgeKind.DERIVED_FROM,
                independent_validation=True,
            ),
        ),
    )

    paths = graph.trace_lineage("claim-c")

    assert len(paths) == 1
    assert paths[0].node_ids == ("claim-c", "source-b", "source-a")
    assert paths[0].root_node_id == "source-a"
    assert paths[0].independent_validation_edges == 1
    assert graph.report().citation_cycles == ()


def test_evidence_graph_reports_citation_cycle_instead_of_hiding_it() -> None:
    graph = EvidenceGraph(
        nodes=(
            EvidenceGraphNode(
                node_id="a",
                kind=EvidenceNodeKind.SOURCE,
                source_id="a",
                observed_at="2026-09-07T00:00:00Z",
            ),
            EvidenceGraphNode(
                node_id="b",
                kind=EvidenceNodeKind.SOURCE,
                source_id="b",
                observed_at="2026-09-07T00:00:00Z",
            ),
        ),
        edges=(
            EvidenceGraphEdge(
                edge_id="e1",
                from_node_id="a",
                to_node_id="b",
                kind=EvidenceEdgeKind.CITES,
            ),
            EvidenceGraphEdge(
                edge_id="e2",
                from_node_id="b",
                to_node_id="a",
                kind=EvidenceEdgeKind.CITES,
            ),
        ),
    )

    assert graph.report().citation_cycles


def test_research_bridge_requests_web_lane_when_gaps_remain() -> None:
    artifact = compile_research_artifact(
        (
            SourceObservation(
                source=_source("a"),
                lineage_id="lineage-1",
            ),
        ),
        (),
        ResearchRequirements(
            min_sources=3,
            min_independent_lineages=2,
            min_primary_sources=1,
        ),
    )

    plan = build_research_routing_plan(
        "improve crawler",
        artifact,
    )

    assert plan.action is ResearchCycleAction.CONTINUE_RESEARCH
    assert plan.required_lanes == ("web_research", "agnes", "evidence")
    assert plan.human_review_required is False


def test_research_bridge_routes_exhausted_contradiction_to_human() -> None:
    claim_a = Claim(
        claim_id="claim-a",
        subject="product-a",
        predicate="current_version",
        object_value="1",
        source_ids=("a",),
        confidence=0.9,
        reliability=Reliability.OBSERVED,
        observed_at="2026-09-07T00:00:00Z",
    )
    claim_b = Claim(
        claim_id="claim-b",
        subject="product-a",
        predicate="current_version",
        object_value="2",
        source_ids=("b",),
        confidence=0.9,
        reliability=Reliability.OBSERVED,
        observed_at="2026-09-07T00:00:00Z",
    )
    artifact = compile_research_artifact(
        (
            SourceObservation(
                source=_source("a", kind=SourceKind.GOVERNMENT),
                lineage_id="official",
                is_primary=True,
            ),
            SourceObservation(
                source=_source("b", kind=SourceKind.ACADEMIC),
                lineage_id="academic",
                independent_validation=True,
            ),
        ),
        (
            ClaimObservation(claim_a),
            ClaimObservation(claim_b),
        ),
        ResearchRequirements(
            min_sources=2,
            min_independent_lineages=2,
            min_primary_sources=1,
        ),
        exclusive_predicates=frozenset({"current_version"}),
    )

    plan = build_research_routing_plan(
        "current product version",
        artifact,
        research_exhausted=True,
    )

    assert plan.action is ResearchCycleAction.HUMAN_REVIEW_REQUIRED
    assert plan.human_review_required is True
    assert plan.required_lanes == ("agnes", "evidence")
