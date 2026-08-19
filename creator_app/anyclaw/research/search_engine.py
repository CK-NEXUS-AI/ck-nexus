"""Search Engine — ค้นหาจาก Google + หลาย search engine.

รองรับ:
- Google Search (ผ่าน Serper API / scraping)
- DuckDuckGo (ฟรี, ไม่ต้อง key)
- GitHub Search (ค้นหา code + repos)
- Stack Overflow Search
- Reddit Search
- Hacker News Search
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass
class SearchResult:
    """ผลการค้นหาหนึ่งรายการ."""

    title: str
    url: str
    snippet: str = ""
    source: str = ""  # google, duckduckgo, github, etc.
    rank: int = 0
    score: float = 0.0


class SearchEngine:
    """ค้นหาจากหลาย search engine.

    วิธีใช้:
        engine = SearchEngine()

        # ค้นหาจากทุก engine
        results = engine.search("AI agent framework 2024")

        # ค้นหาเฉพาะ GitHub
        results = engine.search("MCP server", sources=["github"])

        # ค้นหาและอ่านเนื้อหา
        detailed = engine.search_and_read("local LLM setup")
    """

    def __init__(self) -> None:
        self._history: list[dict] = []

    def search(
        self,
        query: str,
        *,
        sources: list[str] | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """ค้นหาจากหลาย sources."""
        if sources is None:
            sources = ["duckduckgo", "github"]

        all_results: list[SearchResult] = []
        for source in sources:
            try:
                if source == "duckduckgo":
                    results = self._search_duckduckgo(query, limit)
                elif source == "github":
                    results = self._search_github(query, limit)
                elif source == "stackoverflow":
                    results = self._search_stackoverflow(query, limit)
                elif source == "reddit":
                    results = self._search_reddit(query, limit)
                elif source == "hackernews":
                    results = self._search_hackernews(query, limit)
                elif source == "serper":
                    results = self._search_serper(query, limit)
                else:
                    continue
                all_results.extend(results)
            except Exception:
                continue

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique: list[SearchResult] = []
        for r in all_results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique.append(r)

        self._history.append({
            "query": query,
            "sources": sources,
            "results_count": len(unique),
            "timestamp": time.time(),
        })
        return unique[:limit * 2]

    def search_and_read(
        self,
        query: str,
        *,
        sources: list[str] | None = None,
        read_limit: int = 5,
    ) -> list[dict]:
        """ค้นหา + อ่านเนื้อหาจาก top results."""
        results = self.search(query, sources=sources, limit=read_limit)
        reader = ContentReader()
        detailed: list[dict] = []
        for r in results[:read_limit]:
            content = reader.read_url(r.url)
            detailed.append({
                "title": r.title,
                "url": r.url,
                "source": r.source,
                "snippet": r.snippet,
                "content_length": len(content) if content else 0,
                "content_preview": (content[:500] if content else ""),
            })
        return detailed

    def _search_duckduckgo(self, query: str, limit: int) -> list[SearchResult]:
        """ค้นหาผ่าน DuckDuckGo (ฟรี)."""
        import requests
        results: list[SearchResult] = []
        try:
            resp = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_redirect": "1"},
                timeout=10,
            )
            data = resp.json()

            # Abstract
            if data.get("AbstractText"):
                results.append(SearchResult(
                    title=data.get("Heading", query),
                    url=data.get("AbstractURL", ""),
                    snippet=data.get("AbstractText", ""),
                    source="duckduckgo",
                    rank=1,
                ))

            # Related topics
            for i, topic in enumerate(data.get("RelatedTopics", [])[:limit]):
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(SearchResult(
                        title=topic.get("Text", "")[:80],
                        url=topic.get("FirstURL", ""),
                        snippet=topic.get("Text", ""),
                        source="duckduckgo",
                        rank=i + 2,
                    ))
        except Exception:
            pass
        return results

    def _search_github(self, query: str, limit: int) -> list[SearchResult]:
        """ค้นหา GitHub repos + code."""
        import requests
        results: list[SearchResult] = []
        try:
            resp = requests.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "sort": "stars", "per_page": limit},
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            data = resp.json()
            for i, repo in enumerate(data.get("items", [])[:limit]):
                results.append(SearchResult(
                    title=repo.get("full_name", ""),
                    url=repo.get("html_url", ""),
                    snippet=f"⭐ {repo.get('stargazers_count', 0)} | {repo.get('description', '')[:100]}",
                    source="github",
                    rank=i + 1,
                ))
        except Exception:
            pass
        return results

    def _search_stackoverflow(self, query: str, limit: int) -> list[SearchResult]:
        """ค้นหา Stack Overflow."""
        import requests
        results: list[SearchResult] = []
        try:
            resp = requests.get(
                "https://api.stackexchange.com/2.3/search/advanced",
                params={
                    "q": query, "order": "desc", "sort": "relevance",
                    "site": "stackoverflow", "pagesize": limit,
                },
                timeout=10,
            )
            data = resp.json()
            for i, item in enumerate(data.get("items", [])[:limit]):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=f"Score: {item.get('score', 0)} | Answers: {item.get('answer_count', 0)}",
                    source="stackoverflow",
                    rank=i + 1,
                ))
        except Exception:
            pass
        return results

    def _search_reddit(self, query: str, limit: int) -> list[SearchResult]:
        """ค้นหา Reddit."""
        import requests
        results: list[SearchResult] = []
        try:
            resp = requests.get(
                "https://www.reddit.com/search.json",
                params={"q": query, "limit": limit, "sort": "relevance"},
                headers={"User-Agent": "CK-NEXUS-Research/1.0"},
                timeout=10,
            )
            data = resp.json()
            for i, post in enumerate(data.get("data", {}).get("children", [])[:limit]):
                pd = post.get("data", {})
                results.append(SearchResult(
                    title=pd.get("title", ""),
                    url=f"https://reddit.com{pd.get('permalink', '')}",
                    snippet=f"r/{pd.get('subreddit', '')} | ⬆ {pd.get('score', 0)} | {pd.get('num_comments', 0)} comments",
                    source="reddit",
                    rank=i + 1,
                ))
        except Exception:
            pass
        return results

    def _search_hackernews(self, query: str, limit: int) -> list[SearchResult]:
        """ค้นหา Hacker News (ผ่าน Algolia)."""
        import requests
        results: list[SearchResult] = []
        try:
            resp = requests.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": query, "tags": "story", "hitsPerPage": limit},
                timeout=10,
            )
            data = resp.json()
            for i, hit in enumerate(data.get("hits", [])[:limit]):
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                results.append(SearchResult(
                    title=hit.get("title", ""),
                    url=url,
                    snippet=f"⬆ {hit.get('points', 0)} | {hit.get('num_comments', 0)} comments | {hit.get('author', '')}",
                    source="hackernews",
                    rank=i + 1,
                ))
        except Exception:
            pass
        return results

    def _search_serper(self, query: str, limit: int) -> list[SearchResult]:
        """ค้นหาผ่าน Serper (Google Search)."""
        import requests
        api_key = os.getenv("SERPER_API_KEY", "")
        if not api_key:
            return []
        results: list[SearchResult] = []
        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": query, "num": limit},
                timeout=10,
            )
            data = resp.json()
            for i, item in enumerate(data.get("organic", [])[:limit]):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="serper",
                    rank=i + 1,
                ))
        except Exception:
            pass
        return results

    @property
    def history(self) -> list[dict]:
        return list(self._history)
