from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def make_client(tmp_path: Path, *, access_token: str = "") -> TestClient:
    settings = Settings(
        database_path=tmp_path / "workspace.db",
        mock_ai=True,
        access_token=access_token,
        rate_limit_per_minute=20,
    )
    return TestClient(create_app(settings))


def test_contextual_workspace_describes_dry_run_and_evidence_boundaries(tmp_path: Path):
    with make_client(tmp_path) as client:
        page = client.get("/")
        assert page.status_code == 200
        phrases = (
            'id="intent-form"',
            'id="plan-panel"',
            "Permission Preview",
            "Dry Run",
            "หลักฐาน",
            "Recovery / Undo",
            "ยังไม่ดำเนินการ",
        )
        for phrase in phrases:
            assert phrase in page.text
        script = client.get("/static/automation.js")
        assert script.status_code == 200
        assert "/api/agnes/plan?" not in script.text
        assert 'fetch("/api/agnes/plan"' in script.text
        assert 'method: "POST"' in script.text
        assert "JSON.stringify({ goal: objective })" in script.text
        assert "innerHTML" not in script.text
        assert "ข้อมูลส่วนตัว" in script.text
        assert "canva.com" not in page.text.lower()
        assert "hubspot.com" not in page.text.lower()
        assert "wix.com" not in page.text.lower()


def test_agnes_plan_is_read_only_and_returns_catalog_permission_preview_data(tmp_path: Path):
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/agnes/plan",
            json={"goal": "ตรวจสอบโค้ดและวางแผนทดสอบ"},
        )
        assert response.status_code == 200
        plan = response.json()
        assert plan["goal"] == "ตรวจสอบโค้ดและวางแผนทดสอบ"
        assert plan["plan_id"].startswith("agnes_plan_")
        assert isinstance(plan["skills"], list)
        assert isinstance(plan["requires_approval"], bool)
        assert client.get(
            "/api/runs",
            params={"session_id": "creator-default"},
        ).json() == []
        assert client.get(
            "/api/agnes/plan",
            params={"goal": "plan"},
        ).status_code == 405


def test_agnes_plan_selects_skills_for_thai_intents(tmp_path: Path):
    with make_client(tmp_path) as client:
        content = client.post(
            "/api/agnes/plan",
            json={"goal": "ช่วยวางแผนสร้างคอนเทนต์สำหรับผู้เริ่มต้น และร่างสคริปต์วิดีโอสั้น"},
        ).json()
        content_ids = {skill["id"] for skill in content["skills"]}
        assert {"brain.plan", "mouth.report"}.issubset(content_ids)

        research = client.post(
            "/api/agnes/plan",
            json={"goal": "ช่วยค้นคว้าข้อมูลและตรวจสอบแหล่งที่มา ก่อนสรุปเป็นรายงาน"},
        ).json()
        research_ids = {skill["id"] for skill in research["skills"]}
        assert {"brain.verify_sources", "eyes.web_research"}.issubset(research_ids)

        coding = client.post(
            "/api/agnes/plan",
            json={"goal": "ช่วยตรวจสอบโค้ด วางแผนทดสอบ และสรุปความเสี่ยง โดยยังไม่แก้ไขไฟล์"},
        ).json()
        coding_ids = {skill["id"] for skill in coding["skills"]}
        assert {"hands.test", "immune.policy_check"}.issubset(coding_ids)


def test_agnes_plan_selects_approval_gated_skills_for_thai_intents(tmp_path: Path):
    with make_client(tmp_path) as client:
        workspace = client.post(
            "/api/agnes/plan",
            json={"goal": "ช่วยเปิดพื้นที่ทำงานแยกสำหรับทดสอบ"},
        ).json()
        workspace_ids = {skill["id"] for skill in workspace["skills"]}
        assert "legs.workspace_open" in workspace_ids
        assert workspace["requires_approval"] is True

        upgrade = client.post(
            "/api/agnes/plan",
            json={"goal": "ช่วยพัฒนาความสามารถตัวเองและตรวจสอบผลลัพธ์"},
        ).json()
        upgrade_ids = {skill["id"] for skill in upgrade["skills"]}
        assert "upgrade.self_improve" in upgrade_ids
        assert upgrade["requires_approval"] is True

        summary = client.post(
            "/api/agnes/plan",
            json={"goal": "สรุปข้อมูลการทำงานของระบบ"},
        ).json()
        summary_ids = {skill["id"] for skill in summary["skills"]}
        assert "eyes.web_research" not in summary_ids


def test_agnes_plan_rejects_empty_and_oversized_goals(tmp_path: Path):
    with make_client(tmp_path) as client:
        assert client.post(
            "/api/agnes/plan",
            json={"goal": "   "},
        ).status_code == 422
        assert client.post(
            "/api/agnes/plan",
            json={"goal": "x" * 4001},
        ).status_code == 422


def test_contextual_workspace_uses_configured_access_gate_for_agnes_plan(tmp_path: Path):
    with make_client(tmp_path, access_token="workspace-test-token") as client:
        denied = client.post("/api/agnes/plan", json={"goal": "plan"})
        assert denied.status_code == 401
        allowed = client.post(
            "/api/agnes/plan",
            json={"goal": "plan"},
            headers={"Authorization": "Bearer workspace-test-token"},
        )
        assert allowed.status_code == 200


def test_workspace_shell_is_collapsible_searchable_and_responsive(tmp_path: Path):
    with make_client(tmp_path) as client:
        automation = client.get("/static/automation.js")
        shell_style = client.get("/static/workspace-shell.css")
        assert automation.status_code == shell_style.status_code == 200
        assert "cknexus_sidebar_collapsed" in automation.text
        assert "ค้นหาเมนู" in automation.text
        assert "nav.append(creator)" in automation.text
        assert "shiftKey" in automation.text
        assert ".sidebar-nav .sidebar-view-link" in shell_style.text
        assert "@media (max-width:560px)" in shell_style.text


def test_theme_modes_and_legacy_control_labels_remain_available(tmp_path: Path):
    with make_client(tmp_path) as client:
        page = client.get("/").text
        labels = (
            "DEEP MIDNIGHT",
            "CLEAN ALABASTER",
            "CYBER AURORA",
            "ดาวน์โหลด TXT",
            "ลบประวัติ session นี้",
            "COMMAND PALETTE",
        )
        for label in labels:
            assert label in page
