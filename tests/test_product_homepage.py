"""Regression checks for the canonical CK-NEXUS product homepage."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "creator_app/web/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "creator_app/web/styles.css").read_text(encoding="utf-8")
JS = (ROOT / "creator_app/web/app.js").read_text(encoding="utf-8")


class HomepageMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])


class ProductHomepageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.markup = HomepageMarkup()
        cls.markup.feed(HTML)

    def test_single_canonical_product_identity(self):
        self.assertIn("CK-NEXUS — Governed AI Platform", HTML)
        self.assertNotIn("CREATOR EDITION", HTML)
        self.assertIn("ONE PLATFORM", HTML)

    def test_agnes_and_core_authority_are_positioned_correctly(self):
        self.assertIn("CK-NEXUS CORE", HTML)
        self.assertIn("AGNES", HTML)
        self.assertIn("ORCHESTRATION", HTML)
        self.assertIn("NO EVIDENCE → NO DONE", HTML)

    def test_workspace_and_evidence_dashboard_are_distinct_surfaces(self):
        self.assertIn("CREATOR WORKSPACE", HTML)
        self.assertIn("/development", self.markup.links)

    def test_all_javascript_dom_contract_ids_exist(self):
        selectors = set(re.findall(r'document\.querySelector\("#([A-Za-z0-9_-]+)"\)', JS))
        self.assertTrue(selectors)
        self.assertFalse(selectors - self.markup.ids)

    def test_layout_has_responsive_architecture_rules(self):
        self.assertIn(".architecture-grid", CSS)
        self.assertIn("@media (max-width: 980px)", CSS)
        self.assertIn("@media (max-width: 600px)", CSS)


if __name__ == "__main__":
    unittest.main()
