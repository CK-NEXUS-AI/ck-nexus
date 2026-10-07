from creator_app.agnes.design_evidence import DesignEvidenceRecord
from creator_app.agnes.design_tokens import DEFAULT_DESIGN_TOKENS, DesignTokens
from creator_app.agnes.persona_contract import AgnesPersonaContract, DEFAULT_AGNES_PERSONA
from creator_app.agnes.ui_state_semantics import UiState, UiStateEvent, state_transition_allowed


def test_default_design_tokens_are_valid() -> None:
    assert DEFAULT_DESIGN_TOKENS.validate() == ()


def test_invalid_design_token_is_rejected() -> None:
    tokens = DesignTokens(active="cyan")
    assert "invalid_color:cyan" in tokens.validate()


def test_default_persona_is_governed() -> None:
    assert DEFAULT_AGNES_PERSONA.validate() == ()


def test_persona_cannot_self_approve() -> None:
    persona = AgnesPersonaContract(allows_self_approval=True)
    assert "self_approval_forbidden" in persona.validate()


def test_design_evidence_requires_sha256_digests() -> None:
    record = DesignEvidenceRecord(
        evidence_id="evd-1",
        proposal_id="proposal-1",
        subject="subject-1",
        kind="verification",
        input_digest="bad",
        output_digest="0" * 64,
        policy_decision="allow",
        verifier="independent-verifier",
        timestamp="2026-08-23T00:00:00Z",
    )
    assert "input_digest_must_be_sha256" in record.validate()


def test_ui_state_changes_only_through_allowed_event_transition() -> None:
    event = UiStateEvent(
        event_id="evt-1",
        event_type="task.started",
        current_state=UiState.REQUESTED,
        next_state=UiState.RUNNING,
        task_id="task-1",
        run_id="run-1",
        correlation_id="corr-1",
        causation_id="cmd-1",
    )
    assert event.validate() == ()
    assert state_transition_allowed(UiState.REQUESTED, UiState.RUNNING)
    assert not state_transition_allowed(UiState.IDLE, UiState.COMPLETED)
