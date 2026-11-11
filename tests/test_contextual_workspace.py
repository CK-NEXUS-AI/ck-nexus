from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def make_client(tmp_path: Path, *, access_token: str = "") -> TestClient:
    return TestClient(
        create_app(
            Settings(
                database_path=tmp_path / "workspace.db",
                mock_ai=True,
                access_token=access_token,
                rate_limit_per_minute=20,
            )
        )
    )


def test_contextual_workspace_describes_dry_run_and_evidence_boundaries(tmp_path: Path):
    with make_client(tmp_path) as client:
        page = client.get("/")
        assert page.status_code == 200
        for phrase in (
            'id="intent-form"',
            'id="plan-panel"',
            "Permission Preview",
            "Dry Run",
            "หลักฐาน",
            "Recovery / Undo",
            "ยังไม่ดำเนินการ",
        ):
            assert phrase in page.text
        assert client.get("/static/automation.css").status_code == 200
        script = client.get("/static/automation.js")
        assert script.status_code == 200
        assert "/api/agnes/plan?" in script.text
        assert "innerHTML" not in script.text
        assert "canva.com" not in page.text.lower()
        assert "hubspot.com" not in page.text.lower()
        assert "wix.com" not in page.text.lower()


def test_agnes_plan_is_read_only_and_returns_catalog_permission_preview_data(tmp_path: Path):
    with make_client(tmp_path) as client:
        response = client.get("/api/agnes/plan", params={"goal": "ตรวจสอบโค้ดและวางแผนทดสอบ"})
        assert response.status_code == 200
        plan = response.json()
        assert plan["goal"] == "ตรวจสอบโค้ดและวางแผนทดสอบ"
        assert plan["plan_id"].startswith("agnes_plan_")
        assert isinstance(plan["skills"], list)
        assert isinstance(plan["requires_approval"], bool)
        assert client.get("/api/runs", params={"session_id": "creator-default"}).json() == []


def test_contextual_workspace_uses_configured_access_gate_for_agnes_plan(tmp_path: Path):
    with make_client(tmp_path, access_token="workspace-test-token") as client:
        denied = client.get("/api/agnes/plan", params={"goal": "plan"})
        assert denied.status_code == 401
        allowed = client.get(
            "/api/agnes/plan",
            params={"goal": "plan"},
            headers={"Authorization": "Bearer workspace-test-token"},
        )
        assert allowed.status_code == 200
