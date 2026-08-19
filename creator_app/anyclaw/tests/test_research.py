"""Tests — Research Intelligence System."""

from __future__ import annotations

from creator_app.anyclaw.research.search_engine import SearchEngine, SearchResult
from creator_app.anyclaw.research.content_reader import ContentReader, PageContent
from creator_app.anyclaw.research.idea_scraper import IdeaScraper, Idea


class TestSearchEngine:
    def test_init(self):
        engine = SearchEngine()
        assert len(engine.history) == 0

    def test_search_result_dataclass(self):
        r = SearchResult(title="Test", url="https://example.com", snippet="desc")
        assert r.title == "Test"
        assert r.source == ""

    def test_search_duckduckgo(self):
        engine = SearchEngine()
        results = engine._search_duckduckgo("Python programming", 3)
        assert isinstance(results, list)

    def test_search_github(self):
        engine = SearchEngine()
        results = engine._search_github("MCP server", 3)
        assert isinstance(results, list)

    def test_history_tracking(self):
        engine = SearchEngine()
        engine.search("test query", sources=["github"])
        assert len(engine.history) == 1


class TestContentReader:
    def test_init(self):
        reader = ContentReader()
        assert reader is not None

    def test_extract_text(self):
        reader = ContentReader()
        html = "<html><body><h1>Title</h1><p>Hello world</p></body></html>"
        text = reader._extract_text(html)
        assert "Hello world" in text

    def test_extract_title(self):
        reader = ContentReader()
        html = "<html><head><title>My Page</title></head></html>"
        title = reader._extract_title(html)
        assert title == "My Page"

    def test_extract_headings(self):
        reader = ContentReader()
        html = "<h1>H1</h1><h2>H2</h2><h3>H3</h3>"
        headings = reader._extract_headings(html)
        assert len(headings) == 3

    def test_page_content(self):
        pc = PageContent(url="https://example.com", title="Test")
        assert pc.url == "https://example.com"
        assert pc.word_count == 0


class TestIdeaScraper:
    def test_init(self):
        scraper = IdeaScraper()
        assert len(scraper.all_ideas) == 0

    def test_idea_dataclass(self):
        idea = Idea(
            title="Test Idea",
            source="github",
            url="https://github.com/test",
            category="feature",
            upvotes=10,
        )
        assert idea.title == "Test Idea"
        assert idea.upvotes == 10

    def test_result_to_idea(self):
        scraper = IdeaScraper()
        r = SearchResult(
            title="Feature Request: Dark Mode",
            url="https://github.com/test/1",
            snippet="⬆ 42 | 5 comments",
            source="github",
        )
        idea = scraper._result_to_idea(r, "test")
        assert idea is not None
        assert idea.category == "feature"
        assert idea.upvotes == 42
        assert idea.comments == 5

    def test_summarize_ideas(self):
        scraper = IdeaScraper()
        ideas = [
            Idea("Idea 1", "github", "https://a.com", upvotes=10),
            Idea("Idea 2", "reddit", "https://b.com", upvotes=5),
        ]
        summary = scraper.summarize_ideas(ideas)
        assert "Idea 1" in summary
        assert "Idea 2" in summary
