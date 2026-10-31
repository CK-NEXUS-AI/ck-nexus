from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def test_development_dashboard_page_and_assets_are_served(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "development-dashboard.db",
        mock_ai=True,
        access_token="",
        rate_limit_per_minute=50,
        dev_team_enabled=True,
        dev_team_web_search_enabled=False,
    )
    with TestClient(create_app(settings)) as client:
        page = client.get("/development")
        css = client.get("/static/development.css")
        js = client.get("/static/development.js")
        approval_page = client.get("/approval")
        approval_asset = client.get("/static/approval.html")
        approval_css = client.get("/static/approval.css")
        approval_js = client.get("/static/approval.js")

    assert approval_page.status_code == 200
    assert approval_asset.status_code == 200
    assert "HUMAN APPROVAL" in approval_page.text
    assert "confirm-check" in approval_page.text
    assert approval_css.status_code == 200
    assert approval_js.status_code == 200
    assert "/api/agnes/approvals" in approval_js.text
    assert "localStorage" not in approval_js.text
    assert page.status_code == 200
    assert "CK-NEXUS" in page.text
    assert "PRE-PRODUCTION" in page.text
    assert css.status_code == 200
    assert js.status_code == 200
    assert "const streams" in js.text
    assert "Merged · PR #332" in js.text
    assert "Merged · Issue closed" in js.text
    assert "1355e5250d08d2041bc80cd0e5867b4b8848b9e4" in js.text
    assert "PR #332" in js.text
    assert "PR #331" in js.text
    assert "PR #334" in js.text
    assert "927 passed, 2 skipped" in js.text
    assert "NOT VERIFIED · NO-GO" in js.text


def test_dashboard_does_not_guess_completion_percentage_and_production_is_no_go() -> None:
    html = Path("creator_app/web/development.html").read_text(encoding="utf-8")
    javascript = Path("creator_app/web/development.js").read_text(encoding="utf-8")

    assert "production_status = NO-GO" in html
    assert "ยังไม่แสดงเปอร์เซ็นต์รวม" in html
    assert "ยังไม่มีสูตรที่ผูก GitHub Issues/Milestones" in html
    assert "43cb6f09b213b00700b165562da51c3ee508641a" in html
    assert "1355e5250d08d2041bc80cd0e5867b4b8848b9e4" in html
    assert "Issue #317 is closed" in html
    assert "2026-11-01T01:39:11+07:00" in html
    assert "PR #334" in html
    assert "927 passed, 2 skipped" in html
    assert "Live: ตรวจไม่พบ service/listener" in html
    assert "AGNES Phase 2/3" in html
    assert "127.0.0.1:8765" in html
    assert "const percent" not in javascript
    assert "Math.round(earned / total * 100)" not in javascript


def test_human_approval_fails_closed_when_access_token_is_not_configured(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "approval-auth.db",
        mock_ai=True,
        access_token="",
        rate_limit_per_minute=50,
        dev_team_enabled=True,
        dev_team_web_search_enabled=False,
    )
    payload = {
        "approval_id": "approval-test-1",
        "fingerprint": "a" * 64,
        "approved_by": "test-reviewer",
        "ttl_seconds": 300,
    }
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/agnes/approvals", json=payload)

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "APPROVAL_AUTH_NOT_CONFIGURED"


def test_human_approval_requires_and_accepts_configured_bearer_token(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "approval-token.db",
        mock_ai=True,
        access_token="test-approval-token",
        rate_limit_per_minute=50,
        dev_team_enabled=True,
        dev_team_web_search_enabled=False,
    )
    payload = {
        "approval_id": "approval-test-authorized",
        "fingerprint": "b" * 64,
        "approved_by": "test-reviewer",
        "ttl_seconds": 300,
    }
    with TestClient(create_app(settings)) as client:
        denied = client.post("/api/agnes/approvals", json=payload)
        approved = client.post(
            "/api/agnes/approvals",
            json=payload,
            headers={"Authorization": "Bearer test-approval-token"},
        )

    assert denied.status_code == 401
    assert approved.status_code == 200
    assert approved.json()["approval_id"] == "approval-test-authorized"
    assert approved.json()["fingerprint"] == "b" * 64
