from __future__ import annotations

import pytest

from creator_app.global_knowledge.tool_discovery import (
    ReviewState,
    ToolCandidate,
    ToolKind,
    plan_tool_search,
    rank_tool_candidates,
)


def test_plan_tool_search_is_bounded_and_deduplicated() -> None:
    queries = plan_tool_search("MCP search connectors", max_queries=5)
    assert len(queries) == 5
    assert len(set(queries)) == len(queries)
    assert any("MCP server" in query for query in queries)


def test_plan_tool_search_rejects_empty_and_oversized_input() -> None:
    with pytest.raises(ValueError, match="query is required"):
        plan_tool_search("  ")
    with pytest.raises(ValueError, match="500 characters"):
        plan_tool_search("x" * 501)


def test_rank_tool_candidates_deduplicates_urls_and_never_auto_approves() -> None:
    candidates = [
        ToolCandidate(
            name="MCP Search Connector",
            url="https://example.test/tool/?ref=search",
            description="Search web sources through an MCP connector",
            kind=ToolKind.MCP,
        ),
        ToolCandidate(
            name="Search Connector mirror",
            url="https://EXAMPLE.test/tool#readme",
            description="Search tools",
            kind=ToolKind.MCP,
        ),
        ToolCandidate(
            name="Approved local search",
            url="https://local.example/search",
            description="Search local documents",
            review_state=ReviewState.APPROVED,
        ),
    ]
    ranked = rank_tool_candidates("MCP search connector", candidates)
    assert len(ranked) == 2
    assert ranked[0].candidate.name == "MCP Search Connector"
    assert ranked[0].disposition == "discovery_only_requires_review"
    assert any(item.disposition == "approved_subject_to_runtime_policy" for item in ranked)
    assert all(
        item.candidate.review_state is not ReviewState.APPROVED
        or item.disposition.startswith("approved")
        for item in ranked
    )


def test_candidate_rejects_non_http_url_and_embedded_credentials() -> None:
    with pytest.raises(ValueError, match=r"http\(s\)"):
        ToolCandidate(name="bad", url="file:///etc/passwd")
    with pytest.raises(ValueError, match="credentials"):
        ToolCandidate(name="bad", url="https://user:pass@example.test/tool")


def test_rank_limit_is_validated() -> None:
    candidate = ToolCandidate(name="search", url="https://example.test/search")
    with pytest.raises(ValueError, match="limit"):
        rank_tool_candidates("search", [candidate], limit=0)
