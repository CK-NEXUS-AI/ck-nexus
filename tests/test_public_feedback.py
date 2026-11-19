from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def make_client(tmp_path: Path, *, token: str = "beta-admin-token") -> TestClient:
    settings = Settings(
        database_path=tmp_path / "cknexus.db",
        mock_ai=True,
        access_token=token,
        rate_limit_per_minute=20,
    )
    return TestClient(create_app(settings))


def payload(**overrides):
    values = {
        "kind": "bug",
        "title": "หน้าแสดงผลค้างหลังส่งงาน",
        "message": "เมื่อกดส่งงานแล้วหน้าแสดงผลค้างและไม่แสดงผลลัพธ์ที่สร้างขึ้น",
        "rating": 2,
        "steps": "เปิดหน้า workspace แล้วกดส่งงาน",
        "expected": "ควรแสดงผลลัพธ์หลังส่งงานสำเร็จ",
        "consent": True,
        "website": "",
    }
    values.update(overrides)
    return values


def test_public_feedback_submit_and_admin_triage(tmp_path: Path):
    with make_client(tmp_path) as client:
        page = client.get("/feedback")
        assert page.status_code == 200
        assert "Public Beta" in page.text

        submitted = client.post("/api/public-feedback", json=payload())
        assert submitted.status_code == 202
        feedback_id = submitted.json()["feedback_id"]
        assert feedback_id.startswith("fb_")

        assert client.get("/api/internal/public-feedback").status_code == 401
        headers = {"Authorization": "Bearer beta-admin-token"}
        reports = client.get("/api/internal/public-feedback", headers=headers)
        assert reports.status_code == 200
        assert reports.json()["reports"][0]["feedback_id"] == feedback_id

        triage = client.post(f"/api/internal/public-feedback/{feedback_id}/triage", headers=headers)
        assert triage.status_code == 200
        body = triage.json()
        assert body["assessment"] == "needs_reproduction"
        assert body["verified"] is False
        assert body["automatic_code_changes"] is False


def test_feedback_rejects_secrets_and_missing_consent(tmp_path: Path):
    with make_client(tmp_path) as client:
        secret = client.post(
            "/api/public-feedback",
            json=payload(message="พบปัญหาและ token=sk-12345678901234567890 ไม่ควรแสดง"),
        )
        assert secret.status_code == 422
        no_consent = client.post("/api/public-feedback", json=payload(consent=False))
        assert no_consent.status_code == 422


def test_feedback_duplicate_and_honeypot_are_safe(tmp_path: Path):
    with make_client(tmp_path) as client:
        first = client.post("/api/public-feedback", json=payload())
        second = client.post("/api/public-feedback", json=payload())
        assert first.status_code == second.status_code == 202
        assert first.json()["feedback_id"] == second.json()["feedback_id"]

        bot = client.post("/api/public-feedback", json=payload(website="spam"))
        assert bot.status_code == 202
        assert bot.json()["feedback_id"] == ""
        assert (
            len(
                client.get(
                    "/api/internal/public-feedback",
                    headers={"Authorization": "Bearer beta-admin-token"},
                ).json()["reports"]
            )
            == 1
        )


def test_feedback_admin_fails_closed_without_admin_token(tmp_path: Path):
    with make_client(tmp_path, token="") as client:
        assert client.get("/api/internal/public-feedback").status_code == 503
