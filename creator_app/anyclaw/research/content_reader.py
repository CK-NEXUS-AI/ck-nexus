"""Content Reader — อ่าน + สกัดเนื้อหาจากเว็บไซต์."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class PageContent:
    """เนื้อหาจากหน้าเว็บหนึ่งหน้า."""

    url: str
    title: str = ""
    text: str = ""
    headings: list[str] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)
    word_count: int = 0
    language: str = "unknown"


class ContentReader:
    """อ่าน + สกัดเนื้อหาจากเว็บไซต์."""

    def read_url(self, url: str) -> str:
        """อ่านเนื้อหาจาก URL — return plain text."""
        import requests
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "CK-NEXUS-Research/1.0"},
                timeout=15,
            )
            resp.raise_for_status()
            return self._extract_text(resp.text)
        except Exception:
            return ""

    def read_full(self, url: str) -> PageContent:
        """อ่านแบบเต็ม — return PageContent."""
        import requests
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "CK-NEXUS-Research/1.0"},
                timeout=15,
            )
            resp.raise_for_status()
            html = resp.text
            title = self._extract_title(html)
            text = self._extract_text(html)
            headings = self._extract_headings(html)
            links = self._extract_links(html)
            return PageContent(
                url=url,
                title=title,
                text=text,
                headings=headings,
                links=links,
                word_count=len(text.split()),
            )
        except Exception:
            return PageContent(url=url)

    def read_multiple(self, urls: list[str]) -> list[PageContent]:
        """อ่านหลาย URL."""
        return [self.read_full(url) for url in urls]

    def summarize(self, url: str, max_words: int = 200) -> str:
        """อ่าน + สรุป."""
        content = self.read_full(url)
        if not content.text:
            return f"ไม่สามารถอ่านจาก {url}"
        words = content.text.split()[:max_words]
        summary = " ".join(words)
        if len(content.text.split()) > max_words:
            summary += "..."
        return f"📄 {content.title}\n🔗 {url}\n📝 {summary}"

    def _extract_text(self, html: str) -> str:
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:50000] if len(text) > 10 else ""

    def _extract_title(self, html: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _extract_headings(self, html: str) -> list[str]:
        headings = re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html, re.DOTALL | re.IGNORECASE)
        return [re.sub(r"<[^>]+>", "", h).strip() for h in headings if h.strip()]

    def _extract_links(self, html: str) -> list[dict]:
        links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        results = []
        for href, text in links[:50]:
            clean = re.sub(r"<[^>]+>", "", text).strip()
            if clean and len(clean) > 2:
                results.append({"url": href, "text": clean[:100]})
        return results
