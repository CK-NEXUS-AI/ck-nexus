from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "database_path": tmp_path / "cknexus-test.db",
        "mock_ai": True,
        "access_token": "",
        "rate_limit_per_minute": 20,
    }
    values.update(overrides)
    return Settings(**values)


def run_payload(**overrides) -> dict:
    values = {
        "agent_id": "script-writer",
        "prompt": "เขียนสคริปต์สั้นเรื่องการเริ่มใช้ AI",
        "session_id": "test-session",
        "audience": "ครีเอเตอร์มือใหม่",
        "platform": "TikTok",
        "tone": "เป็นกันเอง",
        "language": "ไทย",
    }
    values.update(overrides)
    return values


def test_health_status_and_security_headers(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]

        status = client.get("/api/status").json()
        assert status["mode"] == "mock"
        assert status["key_configured"] is False
        assert status["access_required"] is False
        assert "codex_enabled" not in status
        assert "codex_ready" not in status
        assert "codex_sandbox" not in status


def test_split_liveness_and_readiness_probes(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        live = client.get("/health/live")
        assert live.status_code == 200
        assert live.json()["live"] is True

        ready = client.get("/health/ready")
        assert ready.status_code == 200
        body = ready.json()
        assert body["ready"] is True
        assert body["degraded"] is False
        assert body["dependencies"][0] == {
            "name": "database",
            "state": "healthy",
            "required": True,
        }


def test_typography_control_hub_is_served_without_external_assets(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "COMMAND PALETTE" in response.text
        assert "DEEP MIDNIGHT" in response.text
        assert "CLEAN ALABASTER" in response.text
        assert "CYBER AURORA" in response.text
        assert "DOWNLOAD TXT" in response.text
        assert "DELETE LOCAL SESSION" in response.text
        assert "googleapis.com" not in response.text

        styles = client.get("/static/styles.css")
        script = client.get("/static/app.js")
        assert styles.status_code == 200
        assert script.status_code == 200
        assert "prefers-reduced-motion" in styles.text
        assert "TOKEN_STORAGE_KEY" in script.text


def test_agent_catalog_contains_sellable_mvp_agents(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.get("/api/agents")
        assert response.status_code == 200
        ids = {agent["id"] for agent in response.json()["agents"]}
        assert ids == {
            "content-strategist",
            "script-writer",
            "repurpose-studio",
            "editorial-reviewer",
        }


def test_mock_run_persists_and_can_be_retrieved(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post("/api/runs", json=run_payload())
        assert response.status_code == 200
        run = response.json()
        assert run["mode"] == "mock"
        assert run["status"] == "completed"
        assert run["id"].startswith("run_")
        assert "Demo Mode" in run["content"]

        history = client.get("/api/runs", params={"session_id": "test-session"})
        assert history.status_code == 200
        assert [item["id"] for item in history.json()] == [run["id"]]

        detail = client.get(f"/api/runs/{run['id']}")
        assert detail.status_code == 200
        assert detail.json()["prompt"] == run["prompt"]


def test_unknown_agent_returns_stable_error(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post(
            "/api/runs",
            json=run_payload(agent_id="not-an-agent"),
        )
        assert response.status_code == 404
        assert response.json()["error"] == "AGENT_NOT_FOUND"


def test_live_mode_without_key_is_blocked_safely(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    live_settings = settings(tmp_path, mock_ai=False)
    with TestClient(create_app(live_settings)) as client:
        response = client.post("/api/runs", json=run_payload())
        assert response.status_code == 503
        assert response.json()["error"] == "OPENAI_API_KEY_MISSING"
        assert "sk-" not in response.text


def test_optional_bearer_token(tmp_path: Path):
    protected = settings(tmp_path, access_token="test-only-token")
    with TestClient(create_app(protected)) as client:
        assert client.get("/api/status").json()["access_required"] is True
        assert client.get("/api/agents").status_code == 401
        response = client.get(
            "/api/agents",
            headers={"Authorization": "Bearer test-only-token"},
        )
        assert response.status_code == 200


def test_legacy_executor_endpoints_are_removed(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.get("/api/codex/status").status_code == 404
        assert client.post(
            "/api/codex/tasks", json={"prompt": "Inspect this project"}
        ).status_code == 404


def test_rate_limit_rejects_excess_generation(tmp_path: Path):
    limited = settings(tmp_path, rate_limit_per_minute=1)
    with TestClient(create_app(limited)) as client:
        assert client.post("/api/runs", json=run_payload()).status_code == 200
        response = client.post("/api/runs", json=run_payload(prompt="โจทย์ที่สอง"))
        assert response.status_code == 429
        assert int(response.headers["retry-after"]) >= 1


def test_request_size_and_session_validation(tmp_path: Path):
    small_limit = settings(tmp_path, max_request_bytes=256)
    with TestClient(create_app(small_limit)) as client:
        response = client.post(
            "/api/runs",
            json=run_payload(prompt="ก" * 500),
        )
        assert response.status_code == 413

    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.get("/api/runs", params={"session_id": "../../escape"})
        assert response.status_code == 422


def test_delete_session_removes_history(tmp_path: Path):
    with TestClient(create_app(settings(tmp_path))) as client:
        client.post("/api/runs", json=run_payload()).raise_for_status()
        response = client.delete("/api/sessions/test-session")
        assert response.status_code == 200
        assert response.json()["records"] == 1
        assert client.get("/api/runs", params={"session_id": "test-session"}).json() == []
