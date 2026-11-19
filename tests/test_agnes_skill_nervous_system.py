from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.agnes_runtime import AgnesNervousSystem, AgnesPolicyViolation
from creator_app.agnes_skills import AgnesSkillRegistry
from creator_app.api import create_app
from creator_app.config import Settings
from creator_app.provider_router import (
    ProviderCapabilities,
    ProviderKind,
    ProviderRouter,
    ProviderRouterPolicy,
)


class _LocalProvider:
    name = "local-test"
    kind = ProviderKind.LOCAL
    capabilities = ProviderCapabilities(features=frozenset({"text"}), models=("local",))

    def is_available(self) -> bool:
        return True

    async def invoke(self, prompt: str) -> str:
        return prompt


def _skill_file() -> Path:
    return Path(__file__).resolve().parents[1] / "creator_app" / "skills" / "agnes" / "SKILL.md"


def test_single_agnes_skill_file_loads_unique_manifest():
    registry = AgnesSkillRegistry.load(_skill_file())
    skills = registry.all()
    assert len(skills) >= 18
    assert len({skill.id for skill in skills}) == len(skills)
    assert registry.get("upgrade.self_improve").approval_required is True


def test_registry_selects_model_watch_and_verification():
    registry = AgnesSkillRegistry.load(_skill_file())
    ids = {
        skill.id
        for skill in registry.select("watch latest ai model news and verify source", limit=6)
    }
    assert "eyes.model_watch_50" in ids
    assert "brain.verify_sources" in ids


def test_append_only_ledger_hash_chain(tmp_path: Path):
    ledger = AppendOnlyLedger(tmp_path / "ledger.jsonl")
    first = ledger.append("one", {"value": 1})
    second = ledger.append("two", {"value": 2})
    state = ledger.verify()
    assert state.valid is True
    assert state.entries == 2
    assert second["previous_hash"] == first["hash"]


def test_append_only_ledger_detects_tampering(tmp_path: Path):
    path = tmp_path / "ledger.jsonl"
    ledger = AppendOnlyLedger(path)
    ledger.append("one", {"value": 1})
    row = json.loads(path.read_text().strip())
    row["payload"]["value"] = 999
    path.write_text(json.dumps(row) + "\n")
    state = ledger.verify()
    assert state.valid is False


def test_agnes_prefers_local_and_does_not_need_user_key(tmp_path: Path):
    router = ProviderRouter([_LocalProvider()], policy=ProviderRouterPolicy(local_first=True))
    agnes = AgnesNervousSystem(
        skill_file=_skill_file(), ledger_path=tmp_path / "ledger.jsonl", provider_router=router
    )
    status = agnes.status()
    assert status["inference"]["ready"] is True
    assert status["inference"]["provider"] == "local-test"
    assert status["policy"]["allow_user_api_keys"] is False


def test_agnes_blocks_user_api_key_and_unapproved_high_impact(tmp_path: Path):
    agnes = AgnesNervousSystem(skill_file=_skill_file(), ledger_path=tmp_path / "ledger.jsonl")
    skill = agnes.registry.get("upgrade.self_improve")
    with pytest.raises(AgnesPolicyViolation):
        agnes.authorize_skill(skill, environment="development", approved=False)
    with pytest.raises(AgnesPolicyViolation):
        agnes.authorize_skill(
            skill, environment="development", approved=True, uses_user_api_key=True
        )


def test_agnes_blocks_production_mutation_even_when_approved(tmp_path: Path):
    agnes = AgnesNervousSystem(skill_file=_skill_file(), ledger_path=tmp_path / "ledger.jsonl")
    skill = agnes.registry.get("hands.code_patch")
    with pytest.raises(AgnesPolicyViolation):
        agnes.authorize_skill(skill, environment="production", approved=True)


def test_self_upgrade_plan_has_no_missing_lifecycle_gap(tmp_path: Path):
    agnes = AgnesNervousSystem(skill_file=_skill_file(), ledger_path=tmp_path / "ledger.jsonl")
    plan = agnes.self_upgrade_plan("upgrade CK-NEXUS")
    steps = [item["step"] for item in plan["steps"]]
    assert len(steps) == 21
    assert "quarantine" in " ".join(steps)
    assert "compile" in " ".join(steps)
    assert "security" in " ".join(steps)
    assert "rollback" in " ".join(steps)
    assert "never delete" in " ".join(steps)
    assert plan["production_gate"] == "R12 remains mandatory"


def test_api_exposes_redacted_agnes_status_and_skill_manifest(tmp_path: Path):
    settings = Settings(
        mock_ai=True,
        database_path=tmp_path / "db.sqlite",
        agnes_ledger_path=tmp_path / "agnes.jsonl",
    )
    with TestClient(create_app(settings)) as client:
        status = client.get("/api/agnes/status")
        assert status.status_code == 200
        body = status.json()
        assert body["agent"] == "AGNES"
        assert body["skill_count"] >= 18
        raw = json.dumps(body)
        assert "OPENAI_API_KEY" not in raw
        assert "AGNES_API_KEY" not in raw

        skills = client.get("/api/agnes/skills")
        assert skills.status_code == 200
        assert len(skills.json()["skills"]) >= 18


def test_api_upgrade_plan_contains_approval_boundary(tmp_path: Path):
    settings = Settings(
        mock_ai=True,
        database_path=tmp_path / "db.sqlite",
        agnes_ledger_path=tmp_path / "agnes.jsonl",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/agnes/upgrade-plan", params={"goal": "self upgrade"})
        assert response.status_code == 200
        body = response.json()
        assert body["safe_auto_boundary"] == 17
        assert "merge" in body["approval_boundary"]


def test_external_skill_discovery_is_quarantine_first(tmp_path: Path):
    agnes = AgnesNervousSystem(skill_file=_skill_file(), ledger_path=tmp_path / "ledger.jsonl")
    review = agnes.discovery.review_candidate(
        source_url="https://unknown.example/skill",
        checksum_present=False,
        license_known=False,
        has_executable_scripts=True,
        requests_credentials=True,
        requests_network=True,
    )
    assert review.state == "quarantined"
    assert review.activation_allowed is False
    assert len(review.reasons) >= 5


def test_model_watch_is_bounded_and_never_auto_promotes(tmp_path: Path):
    agnes = AgnesNervousSystem(skill_file=_skill_file(), ledger_path=tmp_path / "ledger.jsonl")
    plan = agnes.model_watch_plan(limit=50)
    assert plan["limit"] == 50
    assert plan["auto_promote_to_runtime"] is False
    assert "superseded" in " ".join(plan["pipeline"])


def test_api_exposes_discovery_and_model_watch_plan(tmp_path: Path):
    settings = Settings(
        mock_ai=True,
        database_path=tmp_path / "db.sqlite",
        agnes_ledger_path=tmp_path / "agnes.jsonl",
    )
    with TestClient(create_app(settings)) as client:
        sources = client.get("/api/agnes/discovery-sources")
        assert sources.status_code == 200
        assert any(item["id"] == "mcp-registry" for item in sources.json()["sources"])
        watch = client.get("/api/agnes/model-watch-plan", params={"limit": 50})
        assert watch.status_code == 200
        assert watch.json()["limit"] == 50
        assert watch.json()["auto_promote_to_runtime"] is False
