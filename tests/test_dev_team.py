from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "database_path": tmp_path / "dev-team.db",
        "mock_ai": True,
        "access_token": "",
        "rate_limit_per_minute": 20,
        "dev_team_enabled": True,
        "dev_team_web_search_enabled": True,
    }
    values.update(overrides)
    return Settings(**values)


def payload(**overrides) -> dict:
    values = {
        "prompt": "ช่วยวิเคราะห์ architecture ของ CK-NEXUS และเสนอสิ่งที่ควรพัฒนาต่อ",
        "session_id": "dev-team-test",
        "consult_mode": "council",
        "context": "Release Candidate ต้องไม่อ้าง Production Ready เกินหลักฐาน",
        "language": "ไทย",
    }
    values.update(overrides)
    return values


def test_dev_team_roster_has_five_advisors(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.get("/api/dev-team")
        assert response.status_code == 200
        body = response.json()
        assert body["enabled"] is True
        assert body["ready"] is True
        assert body["orchestrator"] == "CK-NEXUS Lead Orchestrator"
        assert len(body["advisors"]) == 5
        ids = {item["id"] for item in body["advisors"]}
        assert ids == {"architect", "research", "designer", "builder", "reviewer"}
        research = next(item for item in body["advisors"] if item["id"] == "research")
        assert research["web_search"] is True
        assert all(item["side_effects"] == "none" for item in body["advisors"])


def test_dev_team_mock_council_runs_without_openai_key(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post("/api/dev-team/run", json=payload())
        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "mock"
        assert body["consult_mode"] == "council"
        assert body["advisors_available"] == 5
        assert "Architect & Strategist" in body["content"]
        assert "Research & Analyst" in body["content"]
        assert "Security / QA / DevOps Reviewer" in body["content"]
        assert "sk-" not in response.text


def test_dev_team_focus_mode_returns_one_perspective_in_demo(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post(
            "/api/dev-team/run",
            json=payload(consult_mode="designer"),
        )
        assert response.status_code == 200
        text = response.json()["content"]
        assert "Product & UX Designer" in text
        assert "Research & Analyst" not in text


def test_dev_team_live_mode_without_key_is_blocked(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    live = settings(tmp_path, mock_ai=False)
    with TestClient(create_app(live)) as client:
        response = client.post("/api/dev-team/run", json=payload(consult_mode="auto"))
        assert response.status_code == 503
        assert response.json()["error"] == "OPENAI_API_KEY_MISSING"
        assert "sk-" not in response.text


def test_dev_team_can_be_disabled(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path, dev_team_enabled=False))) as client:
        roster = client.get("/api/dev-team").json()
        assert roster["enabled"] is False
        assert roster["ready"] is False
        response = client.post("/api/dev-team/run", json=payload())
        assert response.status_code == 503
        assert response.json()["detail"]["error"] == "DEV_TEAM_DISABLED"



def test_dev_team_mock_debate_reuses_existing_council(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post(
            "/api/dev-team/run",
            json=payload(consult_mode="debate"),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "mock"
    assert body["consult_mode"] == "debate"
    assert body["advisors_available"] == 5
    assert "CK-NEXUS Debate Protocol V1" in body["content"]
    assert "CONSENSUS_REACHED" in body["content"]
    assert "authority_effect: NONE" in body["content"]
    assert "Production authorization" in body["content"]
    assert "sk-" not in response.text
