"""Evidence-first discovery and ranking for tools that may extend CK-NEXUS.

This module proposes tools only. It never installs, executes, enables, or promotes
an external tool. Search hits remain OBSERVED until independently reviewed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urlsplit, urlunsplit


class ToolKind(StrEnum):
    MCP = "mcp"
    API = "api"
    CLI = "cli"
    SDK = "sdk"
    WEB_SERVICE = "web_service"
    DATA_SOURCE = "data_source"
    LIBRARY = "library"
    UNKNOWN = "unknown"


class ReviewState(StrEnum):
    OBSERVED = "observed"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ToolCandidate:
    """A discovered candidate; presence here grants no permission to run it."""

    name: str
    url: str
    description: str = ""
    kind: ToolKind = ToolKind.UNKNOWN
    capabilities: tuple[str, ...] = ()
    source_query: str = ""
    observed_at: str | None = None
    review_state: ReviewState = ReviewState.OBSERVED
    requires_credentials: bool = False
    has_write_actions: bool = False
    supports_local_execution: bool = False
    evidence_urls: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("candidate name is required")
        parts = urlsplit(self.url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError("candidate URL must be an absolute http(s) URL")
        if parts.username or parts.password:
            raise ValueError("candidate URL must not contain credentials")


@dataclass(frozen=True, slots=True)
class RankedTool:
    candidate: ToolCandidate
    score: float
    matched_terms: tuple[str, ...]
    disposition: str


def plan_tool_search(query: str, *, max_queries: int = 6) -> tuple[str, ...]:
    """Build bounded search queries for tool discovery from one user intent."""
    normalized = " ".join(query.split())
    if not normalized:
        raise ValueError("query is required")
    if len(normalized) > 500:
        raise ValueError("query must be <= 500 characters")
    if not 1 <= max_queries <= 12:
        raise ValueError("max_queries must be within 1..12")

    lower = normalized.casefold()
    queries = [
        f'"{normalized}" tool integration',
        f"{normalized} open source API SDK",
        f"{normalized} MCP server",
        f"{normalized} GitHub repository",
    ]
    if any(term in lower for term in ("search", "research", "discover", "ค้นหา", "สืบค้น")):
        queries.extend((f"{normalized} search connector", f"{normalized} data source API"))
    return tuple(dict.fromkeys(queries))[:max_queries]


def rank_tool_candidates(
    query: str,
    candidates: tuple[ToolCandidate, ...] | list[ToolCandidate],
    *,
    limit: int = 20,
) -> tuple[RankedTool, ...]:
    """Rank candidates by lexical relevance, with safety signals kept separate.

    This score is a discovery aid, not a trust score. Unknown/unreviewed tools
    are never described as approved and must not be auto-executed.
    """
    if not query.strip():
        raise ValueError("query is required")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be within 1..100")

    terms = _tokens(query)
    best_by_url: dict[str, RankedTool] = {}
    for candidate in candidates:
        searchable_text = " ".join(
            (candidate.name, candidate.description, *candidate.capabilities)
        )
        searchable = _tokens(searchable_text)
        matched = tuple(sorted(terms.intersection(searchable)))
        score = 0.0 if not terms else round(len(matched) / len(terms), 4)
        if candidate.review_state is ReviewState.REJECTED:
            disposition = "rejected_do_not_integrate"
        elif candidate.review_state is ReviewState.APPROVED:
            disposition = "approved_subject_to_runtime_policy"
        else:
            disposition = "discovery_only_requires_review"
        item = RankedTool(candidate, score, matched, disposition)
        key = _canonical_url(candidate.url)
        previous = best_by_url.get(key)
        if previous is None or (item.score, len(item.matched_terms)) > (
            previous.score,
            len(previous.matched_terms),
        ):
            best_by_url[key] = item

    return tuple(
        sorted(
            best_by_url.values(),
            key=lambda item: (
                -item.score,
                -len(item.matched_terms),
                item.candidate.name.casefold(),
            ),
        )[:limit]
    )


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in re.findall(r"[\w+#.-]+", value) if len(token) > 1}


def _canonical_url(value: str) -> str:
    parts = urlsplit(value)
    host = (parts.hostname or "").casefold()
    is_default_port = (
        (parts.scheme == "http" and parts.port == 80)
        or (parts.scheme == "https" and parts.port == 443)
    )
    if parts.port and not is_default_port:
        host = f"{host}:{parts.port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.casefold(), host, path, "", ""))
