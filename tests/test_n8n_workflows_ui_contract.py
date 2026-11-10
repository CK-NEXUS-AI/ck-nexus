from __future__ import annotations

import os
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "creator_app/web/n8n-workflows.html"
GATEWAY_PATH = Path(
    os.getenv(
        "CKNEXUS_N8N_GATEWAY_PATH",
        str(ROOT / "ops/vps/services/cknexus_n8n_workflows_ui.py"),
    )
)


class _InlineScriptExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._inside_script = False
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "script":
            self._inside_script = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            self._inside_script = False

    def handle_data(self, data: str) -> None:
        if self._inside_script:
            self.scripts.append(data)


def inline_scripts(source: str) -> str:
    parser = _InlineScriptExtractor()
    parser.feed(source)
    parser.close()
    return "\n".join(parser.scripts)


def html() -> str:
    return HTML_PATH.read_text(encoding="utf-8")


def test_dashboard_has_thai_navigation_for_all_primary_areas():
    source = html()
    assert 'lang="th"' in source
    for label in ("ภาพรวม", "สร้าง Workflow", "แผนผัง", "งานทั้งหมด", "ประวัติการทำงาน", "การเชื่อมต่อ"):
        assert label in source


def test_dashboard_has_real_data_and_clear_empty_error_and_loading_states():
    source = html()
    for phrase in ("กำลังโหลด", "ไม่พบ Workflow", "โหลดข้อมูลไม่สำเร็จ", "ยังไม่รองรับ", "ตรวจสอบล่าสุด"):
        assert phrase in source
    assert "fetch('/api/workflows'" in source or 'fetch("/api/workflows"' in source
    assert "fetch('/api/health'" in source or 'fetch("/api/health"' in source


def test_untrusted_workflow_values_are_not_interpolated_into_inner_html():
    source = html()
    js = inline_scripts(source)
    # API-derived workflow fields must be inserted through DOM text APIs.
    assert "textContent" in js
    assert not any(
        "innerHTML" in line
        and any(value in line for value in ("w.name", "w.id", "w.tags", "d.error", "e.message"))
        for line in js.splitlines()
    )
    assert "<script>" not in js


def test_refresh_controls_prevent_overlapping_requests_and_recover_after_failure():
    source = html()
    assert "AbortController" in source or "loading" in source
    assert "finally" in source
    assert "disabled" in source


def test_gateway_has_only_confirmed_read_routes_and_does_not_expose_secrets():
    source = GATEWAY_PATH.read_text(encoding="utf-8")
    assert "ALLOWED_READ_PATHS" in source
    assert '"workflows"' in source and '"executions"' in source
    assert "X-N8N-API-KEY" in source
    assert "test-secret-sentinel" not in source
    assert "api_key" not in html().lower()


def test_api_rendering_uses_text_nodes_and_never_html_parser():
    source = html()
    js = inline_scripts(source)
    assert "createElement" in js
    assert "textContent = String(value ?? '')" in js
    assert "replaceChildren" in js
    assert "innerHTML" not in js


def test_navigation_exposes_only_supported_and_explicitly_unsupported_features():
    source = html()
    assert 'id="page-workflows"' in source
    assert 'id="page-overview"' in source
    for page in ("builder", "editor", "history", "connections"):
        assert f'id="page-{page}"' in source
    assert "ยังไม่รองรับ" in source
    assert "ไม่ใช้ข้อมูลจำลอง" not in source or "สถานะจริงเท่านั้น" in source
