import os
from pathlib import Path

import pytest

from creator_app.development_control import (
    COMPETENCY_CRITERIA,
    CompetencyLevel,
    DevelopmentState,
    DevelopmentStatusStore,
    default_development_status_db_path,
    evaluate_competency,
)


def _all_answers(value: bool = True) -> dict[str, bool]:
    return {
        criterion: value
        for level in COMPETENCY_CRITERIA.values()
        for criterion in level
    }


def test_competency_pro_requires_human_confirmation_for_write() -> None:
    assessment = evaluate_competency(
        agent_id="ai-1",
        display_name="Agent One",
        answers=_all_answers(),
        human_confirmed=False,
    )
    assert assessment.level is CompetencyLevel.PRO_LEVEL
    assert assessment.write_allowed is False


def test_competency_pro_human_confirmed_can_write_development_branch() -> None:
    assessment = evaluate_competency(
        agent_id="ai-1",
        display_name="Agent One",
        answers=_all_answers(),
        human_confirmed=True,
    )
    assert assessment.level is CompetencyLevel.PRO_LEVEL
    assert assessment.write_allowed is True
    assert "write_development_branch" in assessment.permissions
    assert "merge_main" not in assessment.permissions
    assert "deploy_production" not in assessment.permissions


def test_level_one_failure_never_gets_pro_write() -> None:
    answers = _all_answers()
    answers[COMPETENCY_CRITERIA["level_1"][0]] = False
    assessment = evaluate_competency(
        agent_id="ai-2",
        display_name="Agent Two",
        answers=answers,
        human_confirmed=True,
    )
    assert assessment.level is CompetencyLevel.OBSERVER
    assert assessment.write_allowed is False


def test_missing_criterion_fails_closed() -> None:
    answers = _all_answers()
    answers.pop(COMPETENCY_CRITERIA["level_4"][0])
    with pytest.raises(ValueError, match="missing competency criteria"):
        evaluate_competency(
            agent_id="ai-3",
            display_name="Agent Three",
            answers=answers,
        )


def test_task_state_machine_and_completion_gate(tmp_path: Path) -> None:
    store = DevelopmentStatusStore(tmp_path / "dev-status.sqlite3")
    task = store.create_task(
        task_id="DEV-001",
        title="Implement live status",
        owner="engineer",
        priority="P0",
        actor="owner",
    )
    assert task["state"] == DevelopmentState.RECEIVED.value

    for state in (
        DevelopmentState.PLANNED,
        DevelopmentState.QUEUED,
        DevelopmentState.RUNNING,
        DevelopmentState.MEASURED,
        DevelopmentState.REVIEW_REQUIRED,
    ):
        task = store.transition_task(
            task_id="DEV-001",
            to_state=state,
            actor="engineer",
        )

    with pytest.raises(PermissionError, match="human review"):
        store.transition_task(
            task_id="DEV-001",
            to_state=DevelopmentState.COMPLETED,
            actor="engineer",
        )

    task = store.transition_task(
        task_id="DEV-001",
        to_state=DevelopmentState.COMPLETED,
        actor="human-reviewer",
        human_reviewed=True,
        merged=True,
        commit_hash="abc123",
        progress=100,
    )
    assert task["state"] == DevelopmentState.COMPLETED.value


def test_skipping_workflow_stage_is_rejected(tmp_path: Path) -> None:
    store = DevelopmentStatusStore(tmp_path / "dev-status.sqlite3")
    store.create_task(
        task_id="DEV-002",
        title="No skipping",
        owner="engineer",
        actor="owner",
    )
    with pytest.raises(ValueError, match="invalid development transition"):
        store.transition_task(
            task_id="DEV-002",
            to_state=DevelopmentState.RUNNING,
            actor="engineer",
        )


def test_blocked_requires_reason(tmp_path: Path) -> None:
    store = DevelopmentStatusStore(tmp_path / "dev-status.sqlite3")
    store.create_task(
        task_id="DEV-003",
        title="Blocked test",
        owner="engineer",
        actor="owner",
    )
    with pytest.raises(ValueError, match="blocker reason"):
        store.transition_task(
            task_id="DEV-003",
            to_state=DevelopmentState.BLOCKED,
            actor="engineer",
        )


def test_snapshot_never_guesses_scores_or_progress(tmp_path: Path) -> None:
    store = DevelopmentStatusStore(tmp_path / "dev-status.sqlite3")
    store.create_task(
        task_id="DEV-004",
        title="Unknown values",
        owner="engineer",
        actor="owner",
    )
    snapshot = store.snapshot()
    assert snapshot["queued"][0]["progress"] is None
    assert snapshot["queued"][0]["eta"] is None
    assert snapshot["scores"]["openssf_scorecard_current"] is None
    assert snapshot["scores"]["unknown_values_are_never_guessed"] is True


def test_team_director_blocks_unassessed_dynamic_agent(tmp_path: Path) -> None:
    from creator_app.ai_team.agent import Agent
    from creator_app.ai_team.agent_models import AgentRole
    from creator_app.ai_team.team_director import TeamDirector

    class CandidateAgent(Agent):
        def process(self, request, context=None):
            raise AssertionError("candidate must not execute before admission")

    team = TeamDirector(
        development_status_path=str(tmp_path / "dev-status.sqlite3")
    )
    candidate = CandidateAgent(
        name="Candidate",
        role=AgentRole.RESEARCHER,
        expertise=("research",),
    )

    with pytest.raises(PermissionError, match="no competency assessment"):
        team.admit_agent(
            "candidate",
            candidate,
            competency_agent_id="candidate-ai",
        )


def test_team_director_admits_human_confirmed_pro_agent(tmp_path: Path) -> None:
    from creator_app.ai_team.agent import Agent
    from creator_app.ai_team.agent_models import AgentRole, TaskStatus
    from creator_app.ai_team.team_director import TeamDirector

    class CandidateAgent(Agent):
        def process(self, request, context=None):
            from creator_app.ai_team.agent_models import TaskResult

            return TaskResult(
                task_id="candidate-task",
                agent_name=self.name,
                agent_role=self.role.value,
                status=TaskStatus.COMPLETED,
                output="ok",
            )

    status_path = tmp_path / "dev-status.sqlite3"
    store = DevelopmentStatusStore(status_path)
    assessment = evaluate_competency(
        agent_id="candidate-ai",
        display_name="Candidate",
        answers=_all_answers(),
        human_confirmed=True,
    )
    store.save_competency(assessment, actor="human-reviewer")

    team = TeamDirector(development_status_path=str(status_path))
    candidate = CandidateAgent(
        name="Candidate",
        role=AgentRole.RESEARCHER,
        expertise=("research",),
    )
    team.admit_agent(
        "candidate",
        candidate,
        competency_agent_id="candidate-ai",
    )

    assert "candidate" in team.agents
    events = store.history(10)
    assert any(event["event_type"] == "AGENT_ADMITTED" for event in events)


def test_empty_agent_identity_fails_closed() -> None:
    with pytest.raises(ValueError, match="agent_id must not be empty"):
        evaluate_competency(
            agent_id=" ",
            display_name="Candidate",
            answers=_all_answers(),
        )

    with pytest.raises(ValueError, match="display_name must not be empty"):
        evaluate_competency(
            agent_id="candidate-ai",
            display_name=" ",
            answers=_all_answers(),
        )


def test_write_authority_requires_human_confirmed_pro(tmp_path: Path) -> None:
    store = DevelopmentStatusStore(tmp_path / "dev-status.sqlite3")
    assessment = evaluate_competency(
        agent_id="candidate-ai",
        display_name="Candidate",
        answers=_all_answers(),
        human_confirmed=False,
    )
    store.save_competency(assessment, actor="automated-assessment")

    with pytest.raises(PermissionError, match="human-confirmed"):
        store.require_write_authority("candidate-ai")

    confirmed = evaluate_competency(
        agent_id="candidate-ai",
        display_name="Candidate",
        answers=_all_answers(),
        human_confirmed=True,
    )
    store.save_competency(confirmed, actor="human-reviewer")
    granted = store.require_write_authority("candidate-ai")
    assert granted["level"] == "PRO_LEVEL"
    assert granted["write_allowed"] is True



def test_default_state_path_uses_home_state_when_writable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)

    assert default_development_status_db_path() == (
        tmp_path / ".local" / "state" / "ck-nexus" / "development-status.sqlite3"
    )


def test_default_state_path_falls_back_for_nonexistent_container_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "nonexistent-home"))
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setattr(
        "creator_app.development_control.tempfile.gettempdir", lambda: str(tmp_path)
    )

    expected = (
        tmp_path
        / f"ck-nexus-state-{os.getuid()}"
        / "development-status.sqlite3"
    )
    assert default_development_status_db_path() == expected
    store = DevelopmentStatusStore(expected)
    assert store.path == expected
    assert expected.is_file()
