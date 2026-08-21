from creator_app.core.computer_use_contract import (
    ComputerActionProposal,
    ComputerActionRisk,
    ComputerEnvironment,
    ComputerUsePolicy,
)
from creator_app.core.durable_runtime import DurableRuntimePolicy, DurableTask, DurableTaskState
from creator_app.core.realtime_multimodal import RealtimeModality, RealtimePolicy, RealtimeSession


def test_high_risk_computer_action_requires_execution_grant() -> None:
    proposal = ComputerActionProposal(
        action_id="a1",
        environment=ComputerEnvironment.DESKTOP,
        action_type="click",
        screenshot_digest="sha256:abc",
        prompt_injection_scan_evidence_ids=["evd:screenshot-safe"],
        risk=ComputerActionRisk.HIGH,
    )
    assert ComputerUsePolicy.execution_allowed(proposal) is False
    proposal.execution_grant_id = "grant-1"
    assert ComputerUsePolicy.execution_allowed(proposal) is True


def test_durable_task_resume_requires_checkpoint_and_token() -> None:
    task = DurableTask(task_id="t1", subject="subject", state=DurableTaskState.SUSPENDED)
    assert DurableRuntimePolicy.can_resume(task) is False
    task.checkpoint_ids.append("cp-1")
    task.resume_token_ref = "credential-ref"
    assert DurableRuntimePolicy.can_resume(task) is True


def test_direct_realtime_connection_requires_ephemeral_credential() -> None:
    session = RealtimeSession(
        session_id="s1",
        provider="provider",
        model="model",
        input_modalities={RealtimeModality.AUDIO, RealtimeModality.VIDEO},
        output_modalities={RealtimeModality.AUDIO},
    )
    assert RealtimePolicy.is_multimodal(session) is True
    assert RealtimePolicy.client_direct_connection_allowed(session) is False
    session.ephemeral_credential_ref = "ephemeral-ref"
    assert RealtimePolicy.client_direct_connection_allowed(session) is True
