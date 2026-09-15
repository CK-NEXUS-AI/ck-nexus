from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from creator_app.development_control import COMPETENCY_CRITERIA
from creator_app.unified_control import install_unified_control


def _answers() -> dict[str, bool]:
    return {
        criterion: True
        for criteria in COMPETENCY_CRITERIA.values()
        for criterion in criteria
    }


def _client(tmp_path, monkeypatch) -> tuple[TestClient, dict[str, str], dict[str, str]]:
    monkeypatch.setenv(
        "CKNEXUS_DEVELOPMENT_STATUS_DB",
        str(tmp_path / "development-status.sqlite3"),
    )
    monkeypatch.setenv("CKNEXUS_HUMAN_APPROVAL_TOKEN", "human-test-token")

    app = FastAPI()
    app.state.settings = SimpleNamespace(
        access_token="control-test-token",
        app_version="test",
    )
    install_unified_control(app)
    client = TestClient(app)
    control = {"Authorization": "Bearer control-test-token"}
    human = {
        **control,
        "X-CKNEXUS-Human-Approval": "human-test-token",
    }
    return client, control, human


def test_observer_or_unconfirmed_pro_cannot_mutate(tmp_path, monkeypatch) -> None:
    client, control, _human = _client(tmp_path, monkeypatch)

    assessment = client.post(
        "/api/control/development/competency/evaluate",
        headers=control,
        json={
            "agent_id": "ai-candidate",
            "display_name": "AI Candidate",
            "answers": _answers(),
            "human_confirmed": False,
            "reviewer_type": "automated",
            "actor": "automated-evaluator",
        },
    )
    assert assessment.status_code == 200
    assert assessment.json()["level"] == "PRO_LEVEL"
    assert assessment.json()["write_allowed"] is False

    blocked = client.post(
        "/api/control/development/tasks",
        headers=control,
        json={
            "task_id": "DEV-API-001",
            "title": "Must remain blocked",
            "owner": "ai-candidate",
            "actor": "ai-candidate",
            "actor_type": "ai",
            "competency_agent_id": "ai-candidate",
        },
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["error"] == "AI_COMPETENCY_WRITE_GATE_BLOCKED"


def test_human_confirmation_requires_separate_authority_token(
    tmp_path,
    monkeypatch,
) -> None:
    client, control, human = _client(tmp_path, monkeypatch)
    payload = {
        "agent_id": "ai-candidate",
        "display_name": "AI Candidate",
        "answers": _answers(),
        "human_confirmed": True,
        "reviewer_type": "human",
        "actor": "human-reviewer",
    }

    denied = client.post(
        "/api/control/development/competency/evaluate",
        headers=control,
        json=payload,
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["error"] == "HUMAN_APPROVAL_REQUIRED"

    allowed = client.post(
        "/api/control/development/competency/evaluate",
        headers=human,
        json=payload,
    )
    assert allowed.status_code == 200
    assert allowed.json()["level"] == "PRO_LEVEL"
    assert allowed.json()["write_allowed"] is True


def test_ai_can_work_after_human_confirmed_pro_but_cannot_complete(
    tmp_path,
    monkeypatch,
) -> None:
    client, control, human = _client(tmp_path, monkeypatch)

    assessment = client.post(
        "/api/control/development/competency/evaluate",
        headers=human,
        json={
            "agent_id": "ai-pro",
            "display_name": "AI Pro",
            "answers": _answers(),
            "human_confirmed": True,
            "reviewer_type": "human",
            "actor": "human-reviewer",
        },
    )
    assert assessment.status_code == 200

    task = client.post(
        "/api/control/development/tasks",
        headers=control,
        json={
            "task_id": "DEV-API-002",
            "title": "Gated development task",
            "owner": "ai-pro",
            "actor": "ai-pro",
            "actor_type": "ai",
            "competency_agent_id": "ai-pro",
            "priority": "P0",
        },
    )
    assert task.status_code == 200
    assert task.json()["state"] == "RECEIVED"

    for state in (
        "PLANNED",
        "QUEUED",
        "RUNNING",
        "MEASURED",
        "REVIEW_REQUIRED",
    ):
        transitioned = client.post(
            "/api/control/development/tasks/DEV-API-002/transition",
            headers=control,
            json={
                "actor": "ai-pro",
                "actor_type": "ai",
                "competency_agent_id": "ai-pro",
                "to_state": state,
            },
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["state"] == state

    ai_complete = client.post(
        "/api/control/development/tasks/DEV-API-002/transition",
        headers=control,
        json={
            "actor": "ai-pro",
            "actor_type": "ai",
            "competency_agent_id": "ai-pro",
            "to_state": "COMPLETED",
            "human_reviewed": True,
            "merged": True,
        },
    )
    assert ai_complete.status_code == 403
    assert ai_complete.json()["detail"]["error"] == "HUMAN_COMPLETION_REQUIRED"

    completed = client.post(
        "/api/control/development/tasks/DEV-API-002/transition",
        headers=human,
        json={
            "actor": "human-reviewer",
            "actor_type": "human",
            "to_state": "COMPLETED",
            "human_reviewed": True,
            "merged": True,
            "progress": 100,
            "commit_hash": "abc123",
        },
    )
    assert completed.status_code == 200
    assert completed.json()["state"] == "COMPLETED"


def test_completion_evidence_rejects_string_booleans(tmp_path, monkeypatch) -> None:
    client, _control, human = _client(tmp_path, monkeypatch)

    created = client.post(
        "/api/control/development/tasks",
        headers=human,
        json={
            "task_id": "DEV-API-003",
            "title": "Strict completion evidence",
            "owner": "human",
            "actor": "human",
            "actor_type": "human",
        },
    )
    assert created.status_code == 200

    for state in (
        "PLANNED",
        "QUEUED",
        "RUNNING",
        "MEASURED",
        "REVIEW_REQUIRED",
    ):
        transitioned = client.post(
            "/api/control/development/tasks/DEV-API-003/transition",
            headers=human,
            json={
                "actor": "human",
                "actor_type": "human",
                "to_state": state,
            },
        )
        assert transitioned.status_code == 200

    invalid = client.post(
        "/api/control/development/tasks/DEV-API-003/transition",
        headers=human,
        json={
            "actor": "human",
            "actor_type": "human",
            "to_state": "COMPLETED",
            "human_reviewed": "false",
            "merged": True,
        },
    )
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["error"] == "BOOLEAN_FIELD_REQUIRED"
