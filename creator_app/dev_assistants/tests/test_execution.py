"""Tests for governed development-assistant execution contracts."""

import pytest

from creator_app.dev_assistants.evidence import ExecutionEvidence, digest_bytes
from creator_app.dev_assistants.execution import (
    DevExecutionContract,
    ExecutionPolicy,
    ExecutionRequest,
    NetworkMode,
)
from creator_app.dev_assistants.orchestrator import DevAssistantFabric


def _fabric_with_aider() -> DevAssistantFabric:
    return DevAssistantFabric(
        path_lookup=lambda command: command if command == "aider" else None
    )


def test_execution_plan_is_fail_closed_and_non_executing() -> None:
    contract = DevExecutionContract(_fabric_with_aider())
    request = ExecutionRequest(
        assistant_id="aider",
        task="Fix one isolated test failure",
        workstream_id="tests-1",
        required_capabilities=("code_edit", "test_fix"),
    )
    plan = contract.build_plan(request)
    assert plan["assistant_available"] is True
    assert plan["command"] == "aider"
    assert plan["execution_state"] == "PLANNED_NOT_EXECUTED"
    assert plan["policy"]["external_mutation_authorized"] is False
    assert plan["policy"]["patch_only_output"] is True
    assert plan["release_evidence"] is False
    assert plan["production_status"] == "NO-GO"


def test_credential_values_are_rejected_in_favor_of_opaque_refs() -> None:
    with pytest.raises(ValueError, match="opaque cred:// references"):
        ExecutionRequest(
            assistant_id="aider",
            task="Review code",
            workstream_id="review-1",
            credential_refs=("raw-secret-value",),
        )


def test_brokered_network_policy_remains_non_mutating() -> None:
    contract = DevExecutionContract(_fabric_with_aider())
    request = ExecutionRequest(
        assistant_id="aider",
        task="Review repository",
        workstream_id="review-2",
        credential_refs=("cred://tenant/provider/ref-1",),
    )
    policy = ExecutionPolicy(network=NetworkMode.BROKERED)
    plan = contract.build_plan(request, policy)
    assert plan["policy"]["network"] == "brokered"
    assert plan["credential_refs"] == ["cred://tenant/provider/ref-1"]
    assert plan["policy"]["external_mutation_authorized"] is False


def test_missing_required_capability_is_rejected() -> None:
    contract = DevExecutionContract(_fabric_with_aider())
    request = ExecutionRequest(
        assistant_id="aider",
        task="Run unsupported workflow",
        workstream_id="unsupported-1",
        required_capabilities=("local_model",),
    )
    with pytest.raises(ValueError, match="lacks required capabilities"):
        contract.build_plan(request)


def test_execution_identity_is_deterministic() -> None:
    contract = DevExecutionContract(_fabric_with_aider())
    request = ExecutionRequest(
        assistant_id="aider",
        task="Fix one isolated test failure",
        workstream_id="tests-1",
    )
    first = contract.build_plan(request)
    second = contract.build_plan(request)
    assert first["execution_id"] == second["execution_id"]
    assert first["request_digest"] == second["request_digest"]


def test_redacted_evidence_contains_only_digests() -> None:
    patch_digest = digest_bytes(b"diff --git a/x b/x")
    stdout_digest = digest_bytes(b"tests passed")
    evidence = ExecutionEvidence(
        execution_id="devexec-0123456789abcdef0123",
        assistant_id="aider",
        result_state="VERIFIED_CANDIDATE",
        patch_digest=patch_digest,
        stdout_digest=stdout_digest,
        exit_code=0,
    ).envelope()
    assert evidence["raw_output_included"] is False
    assert len(evidence["evidence_digest"]) == 64
    assert evidence["evidence"]["release_evidence"] is False


def test_invalid_digest_is_rejected() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        ExecutionEvidence(
            execution_id="devexec-0123456789abcdef0123",
            assistant_id="aider",
            result_state="FAILED",
            patch_digest="not-a-digest",
        )
