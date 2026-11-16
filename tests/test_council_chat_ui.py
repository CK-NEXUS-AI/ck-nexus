from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings


def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "council-chat.db",
        mock_ai=True,
        access_token="",
        rate_limit_per_minute=50,
        dev_team_enabled=True,
        dev_team_web_search_enabled=True,
    )


def test_dev_team_roster_exposes_direct_chat_capabilities(tmp_path: Path) -> None:
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.get("/api/dev-team")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["model"]
    assert "debate" in body["consult_modes"]
    assert body["debate"]["authority_effect"] == "NONE"
    assert body["debate"]["consensus_threshold"] == 0.8
    assert body["debate"]["max_words_per_turn"] == 300
    assert body["side_effect_policy"].startswith("advisory-only")


def test_debate_run_exposes_structured_execution_metadata(tmp_path: Path) -> None:
    payload = {
        "prompt": "ถกเถียงว่าควรเพิ่ม Debate Protocol เข้า Development Council หรือไม่",
        "session_id": "council-chat-test",
        "consult_mode": "debate",
        "context": "Development only; do not claim Production Ready.",
        "language": "ไทย",
    }

    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post("/api/dev-team/run", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "mock"
    assert body["provider"] == "mock"
    assert body["advisory_only"] is True
    assert body["workflow"] == [
        "PROPOSER",
        "OPPOSER",
        "EXAMINER",
        "SYNTHESIZER",
        "DETERMINISTIC_MODERATOR",
    ]
    assert body["debate_status"] == "CONSENSUS_REACHED"
    assert body["consensus_score"] == 1.0
    assert body["evidence_ref_count"] == 3
    assert "authority_effect: NONE" in body["content"]
    assert "not independent human review" in body["content"]


def test_full_system_demo_has_direct_council_chat_controls(tmp_path: Path) -> None:
    with TestClient(create_app(settings(tmp_path))) as client:
        page = client.get("/demo")
        script = client.get("/static/full-system.js")

    assert page.status_code == 200
    assert script.status_code == 200

    html = page.text
    assert 'id="dev-team-chat"' in html
    assert 'data-dev-mode="debate"' in html
    assert 'data-dev-quick="debate"' in html
    assert 'data-dev-quick="reviewer"' in html
    assert 'data-dev-quick="research"' in html
    assert 'id="dev-run-consensus"' in html
    assert 'id="dev-run-evidence"' in html

    javascript = script.text
    assert "async function runDevTeam" in javascript
    assert "appendCouncilMessage" in javascript
    assert "PREVIOUS COUNCIL OUTPUT" in javascript
    assert "DEBATE คำตอบล่าสุด" not in javascript


def test_chat_cors_allows_only_explicit_configured_origin(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CKNEXUS_CHAT_ALLOWED_ORIGINS", "https://ck-nexus-ai.github.io")
    with TestClient(create_app(settings(tmp_path))) as client:
        allowed = client.options(
            "/api/chat/status",
            headers={
                "Origin": "https://ck-nexus-ai.github.io",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        denied = client.options(
            "/api/chat/status",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://ck-nexus-ai.github.io"
    assert "access-control-allow-origin" not in denied.headers


def test_chat_cors_rejects_wildcard_origin_configuration(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CKNEXUS_CHAT_ALLOWED_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="wildcard is forbidden"):
        create_app(settings(tmp_path))


def test_public_chat_ui_uses_only_scoped_chat_api_and_session_storage():
    root = Path(__file__).resolve().parents[1]
    javascript = (root / "docs" / "assets" / "chat.js").read_text(encoding="utf-8")
    html = (root / "docs" / "index.html").read_text(encoding="utf-8")

    assert 'request("/api/chat/status")' in javascript
    assert 'request("/api/chat",' in javascript
    assert 'request("/api/dev-team")' not in javascript
    assert 'request("/api/agnes/status")' not in javascript
    assert 'sessionStorage.setItem("ck_chat_token",token)' in javascript
    assert "localStorage" not in javascript
    assert "CK-NEXUS CHAT ACCESS TOKEN" in html
    assert (
        'const DEFAULT_API_BASE="https://emerging-peoples-sheer-open.trycloudflare.com"'
        in javascript
    )
