from __future__ import annotations

from datetime import UTC
from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def test_development_dashboard_page_and_assets_are_served(tmp_path: Path) -> None:
    settings = Settings(
        database_path=tmp_path / "development-dashboard.db", mock_ai=True,
        access_token="status-token", rate_limit_per_minute=50,
        dev_team_enabled=True, dev_team_web_search_enabled=False,
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
    assert "LIVE SNAPSHOT" in page.text
    assert css.status_code == 200
    assert js.status_code == 200
    assert 'fetch("/api/dev-status"' in js.text


def test_dashboard_does_not_embed_operational_claims() -> None:
    html = Path("creator_app/web/development.html").read_text(encoding="utf-8")
    javascript = Path("creator_app/web/development.js").read_text(encoding="utf-8")
    for content in (html, javascript):
        for forbidden in ("PR #", "Issue #", "927", "81%", "NO-GO", "const streams"):
            assert forbidden not in content


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


def test_dev_status_api_reads_fresh_stale_and_missing_snapshot(tmp_path: Path, monkeypatch) -> None:
    import json
    from datetime import datetime, timedelta

    status_file = tmp_path / "dev_status.json"
    monkeypatch.setenv("CKNEXUS_DEV_STATUS_FILE", str(status_file))
    settings = Settings(
        database_path=tmp_path / "dev-status-api.db", mock_ai=True,
        access_token="status-token", rate_limit_per_minute=50,
        dev_team_enabled=True, dev_team_web_search_enabled=False,
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/dev-status").status_code == 401
        headers = {"Authorization": "Bearer status-token"}
        missing = client.get("/api/dev-status", headers=headers)
        assert missing.status_code == 200 and missing.json()["stale"] is True
        fresh = {"collected_at": datetime.now(UTC).isoformat(),
                 "items": {"git": {"value": {"head": "abc123"}, "source": "git",
                 "collected_at": datetime.now(UTC).isoformat(), "status": "ok"}}}
        status_file.write_text(json.dumps(fresh), encoding="utf-8")
        response = client.get("/api/dev-status", headers=headers)
        assert response.status_code == 200 and response.json()["stale"] is False
        fresh["collected_at"] = (datetime.now(UTC) - timedelta(seconds=601)).isoformat()
        status_file.write_text(json.dumps(fresh), encoding="utf-8")
        stale = client.get("/api/dev-status", headers=headers)
        assert stale.status_code == 200 and stale.json()["stale"] is True


def test_dashboard_has_no_embedded_status_claims() -> None:
    html = Path("creator_app/web/development.html").read_text(encoding="utf-8")
    javascript = Path("creator_app/web/development.js").read_text(encoding="utf-8")
    for content in (html, javascript):
        for forbidden in ("PR #", "Issue #", "927", "81%", "NO-GO", "const streams"):
            assert forbidden not in content
    assert 'fetch("/api/dev-status"' in javascript
    assert "setInterval(refresh, 30000)" in javascript
    assert "ข้อมูลเก่า/ตรวจไม่ได้" in javascript
