"""Idea Scraper — ค้นหาไอเดียจากผู้ใช้และผู้พัฒนาทุกระดับ.

ค้นหาจาก:
- GitHub Issues/PRs (feature requests, bug reports)
- Stack Overflow (questions, answers)
- Reddit (discussions, ideas)
- Hacker News (projects, discussions)
- Product Hunt (new products)
- Dev.to / Medium (articles, tutorials)
- Twitter/X (trends, ideas)
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from creator_app.anyclaw.research.content_reader import ContentReader
from creator_app.anyclaw.research.search_engine import SearchEngine


@dataclass
class Idea:
    """ไอเดียหนึ่งชิ้น."""

    title: str
    source: str
    url: str
    description: str = ""
    category: str = ""  # feature, bug, tutorial, discussion, project
    upvotes: int = 0
    comments: int = 0
    tags: tuple[str, ...] = ()
    discovered_at: float = 0.0


class IdeaScraper:
    """ค้นหาไอเดียจากทุก platform.

    วิธีใช้:
        scraper = IdeaScraper()

        # ค้นหาไอเดียเกี่ยวกับ AI agents
        ideas = scraper.find_ideas("AI agent framework")

        # ค้นหา trending projects
        trending = scraper.find_trending("local LLM")

        # ค้นหาและอ่านรายละเอียด
        detailed = scraper.deep_research("MCP protocol")
    """

    def __init__(self) -> None:
        self._search = SearchEngine()
        self._reader = ContentReader()
        self._ideas: list[Idea] = []
        self._history: list[dict] = []

    def find_ideas(self, topic: str, *, limit: int = 20) -> list[Idea]:
        """ค้นหาไอเดียจากทุก platform."""
        queries = [
            f"{topic} feature request",
            f"{topic} ideas",
            f"{topic} wishlist",
            f"{topic} improvement",
            f"{topic} best practices",
        ]

        sources = ["github", "stackoverflow", "reddit", "hackernews"]
        all_ideas: list[Idea] = []

        for query in queries:
            results = self._search.search(query, sources=sources, limit=limit // len(queries))
            for r in results:
                idea = self._result_to_idea(r, topic)
                if idea:
                    all_ideas.append(idea)

        # Deduplicate
        seen: set[str] = set()
        unique: list[Idea] = []
        for idea in all_ideas:
            if idea.url not in seen:
                seen.add(idea.url)
                unique.append(idea)

        # Sort by relevance
        unique.sort(key=lambda i: i.upvotes + i.comments * 2, reverse=True)

        self._ideas.extend(unique[:limit])
        self._history.append({
            "topic": topic,
            "ideas_found": len(unique),
            "timestamp": time.time(),
        })
        return unique[:limit]

    def find_trending(self, topic: str) -> list[Idea]:
        """ค้นหา trending projects."""
        results = self._search.search(
            f"{topic} trending 2024 2025",
            sources=["github", "hackernews"],
            limit=15,
        )
        ideas = []
        for r in results:
            idea = self._result_to_idea(r, topic)
            if idea:
                ideas.append(idea)
        return ideas

    def deep_research(self, topic: str, *, read_limit: int = 5) -> list[dict]:
        """ค้นหา + อ่านรายละเอียดจาก top results."""
        detailed = self._search.search_and_read(
            topic,
            sources=["github", "stackoverflow", "hackernews"],
            read_limit=read_limit,
        )
        return detailed

    def find_from_developer(
        self, developer_level: str, topic: str
    ) -> list[Idea]:
        """ค้นหาตามระดับ developer."""
        level_queries = {
            "beginner": f"{topic} tutorial beginner getting started",
            "intermediate": f"{topic} best practices intermediate tips",
            "advanced": f"{topic} architecture advanced optimization",
            "expert": f"{topic} deep dive internals implementation",
        }
        query = level_queries.get(developer_level, topic)
        results = self._search.search(query, sources=["stackoverflow", "reddit", "hackernews"], limit=10)
        return [idea for r in results if (idea := self._result_to_idea(r, topic))]

    def find_all_levels(self, topic: str) -> dict[str, list[Idea]]:
        """ค้นหาทุกระดับ developer."""
        levels = {}
        for level in ["beginner", "intermediate", "advanced", "expert"]:
            levels[level] = self.find_from_developer(level, topic)
        return levels

    def summarize_ideas(self, ideas: list[Idea]) -> str:
        """สรุปไอเดียทั้งหมด."""
        lines = [f"💡 ไอเดียที่ค้นพบ: {len(ideas)} รายการ", ""]
        for i, idea in enumerate(ideas[:10], 1):
            lines.append(f"{i}. {idea.title}")
            lines.append(f"   📍 {idea.source} | ⬆ {idea.upvotes} | 💬 {idea.comments}")
            lines.append(f"   🔗 {idea.url}")
            if idea.description:
                lines.append(f"   📝 {idea.description[:100]}")
            lines.append("")
        return "\n".join(lines)

    @property
    def all_ideas(self) -> list[Idea]:
        return list(self._ideas)

    def _result_to_idea(self, result: object, topic: str) -> Idea | None:
        """แปลง SearchResult เป็น Idea."""
        title = getattr(result, "title", "")
        url = getattr(result, "url", "")
        snippet = getattr(result, "snippet", "")
        source = getattr(result, "source", "")

        if not title or not url:
            return None

        # Parse upvotes/comments from snippet
        upvotes = 0
        comments = 0
        import re
        up_match = re.search(r"⬆\s*(\d+)", snippet)
        if up_match:
            upvotes = int(up_match.group(1))
        star_match = re.search(r"⭐\s*([\d,]+)", snippet)
        if star_match:
            upvotes = int(star_match.group(1).replace(",", ""))
        comment_match = re.search(r"(\d+)\s*comments?", snippet)
        if comment_match:
            comments = int(comment_match.group(1))

        # Determine category
        category = "discussion"
        title_lower = title.lower()
        if any(w in title_lower for w in ["feature", "request", "proposal", "rfc"]):
            category = "feature"
        elif any(w in title_lower for w in ["bug", "error", "fix", "issue"]):
            category = "bug"
        elif any(w in title_lower for w in ["tutorial", "guide", "how to", "getting started"]):
            category = "tutorial"
        elif any(w in title_lower for w in ["project", "release", "launch", "show"]):
            category = "project"

        return Idea(
            title=title[:200],
            source=source,
            url=url,
            description=snippet[:500],
            category=category,
            upvotes=upvotes,
            comments=comments,
            discovered_at=time.time(),
        )
