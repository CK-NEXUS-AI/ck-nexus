from pathlib import Path

import pytest

from creator_app.core.chat_bridge import BridgeCommand, CKNexusChatBridge
from creator_app.core.checkpoint_guard import CheckpointBinding, CheckpointGuard
from creator_app.core.computer_use_contract import (
    ComputerActionProposal,
    ComputerActionRisk,
    ComputerEnvironment,
    ComputerUsePolicy,
)
from creator_app.core.durable_persistence import JsonlDurableStore
from creator_app.core.durable_runtime import DurableTask
from creator_app.core.fanout_fanin_budget import BudgetPolicy, FanoutFaninBudgetController
from creator_app.core.policy_errors import BudgetExceeded, PolicyViolation


@pytest.mark.security
def test_a01_screenshot_prompt_injection_requires_scan_evidence() -> None:
    proposal = ComputerActionProposal(
        action_id="A-01",
        environment=ComputerEnvironment.BROWSER,
        action_type="click",
        screenshot_digest="sha256:injected-screen",
        prompt_injection_scan_evidence_ids=[],
        risk=ComputerActionRisk.HIGH,
        execution_grant_id="grant:test",
    )
    with pytest.raises(PolicyViolation):
        ComputerUsePolicy.require_execution_allowed(proposal)


@pytest.mark.security
def test_a02_raw_credential_rejected_from_durable_state(tmp_path: Path) -> None:
    store = JsonlDurableStore(tmp_path / "state.jsonl")
    task = DurableTask(
        task_id="A-02",
        subject="credential-exfiltration",
        resume_token_ref="API_KEY=raw-secret-value",
    )
    with pytest.raises(ValueError):
        store.append_task(task)
    assert not (tmp_path / "state.jsonl").exists()


@pytest.mark.security
def test_a03_tool_call_spoofing_is_blocked() -> None:
    bridge = CKNexusChatBridge()
    bridge.enable_read_only(governor_approved=True)
    with pytest.raises(PolicyViolation):
        bridge.execute(BridgeCommand(command="shell.exec"))


@pytest.mark.security
def test_a04_checkpoint_rollback_hash_mismatch_stops_execution() -> None:
    binding = CheckpointBinding(
        checkpoint_id="cp:A-04",
        expected_version_hash="sha256:new",
        observed_version_hash="sha256:old",
    )
    with pytest.raises(PolicyViolation):
        CheckpointGuard.require_version_match(binding)


@pytest.mark.security
def test_a05_swarm_overload_rejected_before_reservation() -> None:
    controller = FanoutFaninBudgetController(
        BudgetPolicy(total_budget=10.0, max_concurrent_workers=8)
    )
    with pytest.raises(BudgetExceeded):
        controller.reserve(estimated_cost=0.1, active_workers=1000)
    assert controller.reserved == 0.0
    assert controller.spent == 0.0
