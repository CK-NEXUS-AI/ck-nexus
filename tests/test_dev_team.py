from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.catalog import get_agent_spec, list_agent_cards
from creator_app.config import Settings
from creator_app.credential_broker import CredentialBroker
from creator_app.dev_team import DevTeamRuntime
from creator_app.providers import build_provider_router
from creator_app.runtime import CreatorRuntime, ProviderRuntimeError
from creator_app.schemas import DevTeamRequest, RunRequest


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


class FakeGeminiRouter:
    def __init__(self):
        self.prompt = ""
        self.invocations = 0

    def preferred_status(self, *, required_capabilities=()):
        if "agents-sdk" in set(required_capabilities):
            return None
        if "text" in set(required_capabilities):
            return SimpleNamespace(
                name="gemini",
                capabilities=SimpleNamespace(models=("gemini-2.5-flash",)),
            )
        return None

    async def invoke_named(self, provider_name, prompt, *, required_capabilities=()):
        assert provider_name == "gemini"
        assert "text" in set(required_capabilities)
        self.prompt = prompt
        self.invocations += 1
        return SimpleNamespace(provider="gemini", output="Gemini single-model response.")

    def report_failure(self, provider_name):
        raise AssertionError("Fallback failure reporting is owned by ProviderRouter.")

    def report_success(self, provider_name):
        raise AssertionError("Gemini invoke_named owns provider health reporting.")


def test_gemini_single_model_fallback_is_ready_and_truthfully_labelled(tmp_path: Path):
    router = FakeGeminiRouter()
    runtime = DevTeamRuntime(
        settings(tmp_path, mock_ai=False, provider_allow_cloud=True),
        provider_router=router,
    )
    request = DevTeamRequest(
        prompt="ช่วยวางแผนพัฒนา CK-NEXUS Chat",
        session_id="gemini-fallback-test",
        consult_mode="council",
        context="Development only.",
        language="ไทย",
    )

    assert runtime.ready is True
    import asyncio

    result = asyncio.run(runtime.run(request))

    assert result.mode == "gemini"
    assert result.provider == "gemini"
    assert result.model == "gemini-2.5-flash"
    assert result.workflow == ["GEMINI_SINGLE_MODEL_FALLBACK"]
    assert result.advisory_only is True
    assert "one model, not five independent agents" in router.prompt
    assert "Do not claim separate specialists were called" in router.prompt
    assert router.invocations == 1


def test_gemini_single_model_prompt_uses_real_line_breaks(tmp_path: Path):
    request = DevTeamRequest(
        prompt="ตรวจสอบระบบ",
        session_id="gemini-prompt-format-test",
        consult_mode="council",
        context="บริบททดสอบ",
        language="ไทย",
    )
    prompt = DevTeamRuntime._build_single_model_input(request)
    assert "\n\nRUNTIME MODE: GEMINI SINGLE-MODEL FALLBACK" in prompt
    assert "\\n" not in prompt


def test_gemini_single_model_fallback_blocks_debate_mode(tmp_path: Path):
    router = FakeGeminiRouter()
    runtime = DevTeamRuntime(
        settings(tmp_path, mock_ai=False, provider_allow_cloud=True),
        provider_router=router,
    )
    request = DevTeamRequest(
        prompt="ถกเถียงข้อเสนอ",
        session_id="gemini-debate-test",
        consult_mode="debate",
        language="ไทย",
    )

    import asyncio

    with pytest.raises(ProviderRuntimeError, match="DEBATE_REQUIRES_MULTI_AGENT"):
        asyncio.run(runtime.run(request))
    assert router.invocations == 0


def test_configured_gemini_provider_enables_truthful_single_model_chat_status(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-a-real-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    configured = settings(
        tmp_path,
        mock_ai=False,
        provider_allow_cloud=True,
        chat_access_token="chat-status-test-token",
    )
    router = build_provider_router(configured, CredentialBroker.from_environment())
    preferred = router.preferred_status(required_capabilities={"text"})
    assert preferred is not None
    assert preferred.name == "gemini"
    assert preferred.capabilities.models[0] == "gemini-2.5-flash"

    with TestClient(create_app(configured)) as client:
        status = client.get("/api/status")
        roster = client.get("/api/dev-team")
        chat_status = client.get(
            "/api/chat/status",
            headers={"Authorization": "Bearer chat-status-test-token"},
        )

    assert chat_status.status_code == 200
    assert chat_status.json()["ready"] is True
    assert chat_status.json()["provider"] == "gemini"
    assert chat_status.json()["chat_mode"] == "single-model-fallback"
    assert chat_status.json()["execution_status"] == "NOT_EXECUTED"
    assert status.status_code == 200
    assert status.json()["mode"] == "gemini"
    assert status.json()["model"] == "gemini-2.5-flash"
    assert roster.status_code == 200
    body = roster.json()
    assert body["ready"] is True
    assert body["chat_mode"] == "single-model-fallback"
    assert body["single_model_fallback"] is True
    assert body["web_search_enabled"] is False
    assert body["debate"]["enabled"] is False


def test_chat_endpoint_requires_a_dedicated_chat_token(tmp_path: Path):
    configured = settings(tmp_path, access_token="global-api-token", chat_access_token="")
    with TestClient(create_app(configured)) as client:
        response = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer global-api-token"},
            json=payload(),
        )
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "CHAT_AUTH_NOT_CONFIGURED"


def test_chat_token_is_scoped_to_chat_routes_and_agnes_plan_is_read_only(tmp_path: Path):
    configured = settings(
        tmp_path,
        access_token="global-api-token",
        chat_access_token="chat-only-test-token",
        mock_ai=True,
    )
    with TestClient(create_app(configured)) as client:
        global_token_chat = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer global-api-token"},
            json=payload(),
        )
        chat_token_roster = client.get(
            "/api/dev-team",
            headers={"Authorization": "Bearer chat-only-test-token"},
        )
        status = client.get(
            "/api/chat/status",
            headers={"Authorization": "Bearer chat-only-test-token"},
        )
        denied = client.post("/api/chat", json=payload())
        allowed = client.post(
            "/api/chat",
            headers={"Authorization": "Bearer chat-only-test-token"},
            json=payload(consult_mode="auto"),
        )

    assert global_token_chat.status_code == 401
    assert chat_token_roster.status_code == 401
    assert status.status_code == 200
    assert status.json()["ready"] is True
    assert status.json()["execution_status"] == "NOT_EXECUTED"
    assert denied.status_code == 401
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["provider"] == "mock"
    assert body["agnes"]["status"] == "PLANNED"
    assert body["agnes"]["execution_status"] == "NOT_EXECUTED"
    assert body["execution_status"] == "NOT_EXECUTED"
    assert body["authority_effect"] == "NONE"
    assert isinstance(body["agnes"]["selected_skills"], list)
    assert "workspace" not in body["agnes"]
    assert "/opt/" not in allowed.text


def test_creator_runtime_uses_gemini_text_adapter_without_agents_sdk(tmp_path: Path):
    router = FakeGeminiRouter()
    configured = settings(tmp_path, mock_ai=False, provider_allow_cloud=True)
    runtime = CreatorRuntime(configured, provider_router=router)
    spec = get_agent_spec(list_agent_cards()[0].id)
    request = RunRequest(
        agent_id=spec.id,
        prompt="เขียนคำอธิบาย CK-NEXUS",
        session_id="creator-gemini-test",
        language="ไทย",
    )

    import asyncio

    result = asyncio.run(runtime.run(spec, request))
    assert result.mode == "gemini"
    assert result.provider == "gemini"
    assert result.model == "gemini-2.5-flash"
    assert result.content == "Gemini single-model response."
    assert router.invocations == 1
