from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from creator_app.credential_broker import CredentialBroker, CredentialId
from fastapi.testclient import TestClient

from creator_app.agnes.execution.adapters.base import ExecutionContext
from creator_app.agnes.execution.approval import StickyApprovalResolver
from creator_app.agnes.execution.dispatcher import (
    DispatcherPolicy,
    SkillExecutionDispatcher,
)
from creator_app.agnes.execution.guards import ExecutionPolicyEngine
from creator_app.agnes.execution.idempotency import InMemoryIdempotencyStore
from creator_app.agnes.execution.kill_switch import KillSwitchHierarchy
from creator_app.agnes.execution.manifest import ImmutableExecutionManifest
from creator_app.agnes.execution.promotion import (
    ArtifactPromotionState,
    CodePatchState,
    can_promote,
)
from creator_app.agnes.execution.request import (
    CredentialRequirement,
    ExecutorRiskClass,
    ExecutorType,
    SkillExecutionRequest,
)
from creator_app.agnes.execution.result import ExecutionStatus, SkillExecutionResult
from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.agnes_runtime import AgnesNervousSystem, AgnesPolicy
from creator_app.agnes_skills import AgnesSkillRegistry
from creator_app.api import create_app
from creator_app.config import Settings


def _skill_file() -> Path:
    return Path(__file__).resolve().parents[1] / "creator_app" / "skills" / "agnes" / "SKILL.md"


def _request(
    skill_id: str = "brain.plan",
    *,
    executor: ExecutorType = ExecutorType.INTERNAL,
    inputs: dict | None = None,
    approval_id: str | None = None,
    environment: str = "development",
    idempotency_key: str | None = "idem-1",
    credential_requirements: tuple[CredentialRequirement, ...] = (),
    granted_capabilities: tuple[str, ...] = (),
) -> SkillExecutionRequest:
    registry = AgnesSkillRegistry.load(_skill_file())
    skill = registry.get(skill_id)
    return SkillExecutionRequest(
        execution_id="exec-1",
        correlation_id="corr-1",
        skill_id=skill.id,
        skill_version=skill.version,
        executor=executor,
        goal="test goal",
        plan_step={"id": skill.id, "executor": executor.value},
        inputs=inputs or {"value": 1},
        tenant_id="tenant-1",
        actor_id="actor-1",
        environment=environment,
        policy_version="r14-phase1",
        workspace_id="ws-1",
        baseline_commit="abc123",
        approval_id=approval_id,
        idempotency_key=idempotency_key,
        credential_requirements=credential_requirements,
        granted_capabilities=granted_capabilities,
    )


@dataclass
class _Executor:
    name: str = "test-internal"
    executor_type: str = "internal"
    risk_class: ExecutorRiskClass = ExecutorRiskClass.READ_ONLY
    calls: int = 0

    async def can_handle(self, request: SkillExecutionRequest) -> bool:
        return request.executor.value == self.executor_type

    async def execute(
        self, request: SkillExecutionRequest, context: ExecutionContext
    ) -> SkillExecutionResult:
        self.calls += 1
        assert context.manifest.input_hash
        return SkillExecutionResult(
            request.execution_id,
            request.skill_id,
            ExecutionStatus.SUCCEEDED,
            output={"ok": True, "echo": request.inputs["value"]},
        )

    async def health(self) -> dict[str, object]:
        return {"ready": True}


def _dispatcher(
    tmp_path: Path,
    *,
    credential_broker: CredentialBroker | None = None,
    durable_high_risk: bool = True,
) -> SkillExecutionDispatcher:
    registry = AgnesSkillRegistry.load(_skill_file())
    policy = AgnesPolicy()
    return SkillExecutionDispatcher(
        skill_registry=registry,
        policy_engine=ExecutionPolicyEngine(policy),
        approval_service=StickyApprovalResolver(),
        ledger=AppendOnlyLedger(tmp_path / "ledger.jsonl"),
        credential_broker=credential_broker,
        kill_switches=KillSwitchHierarchy(),
        idempotency_store=InMemoryIdempotencyStore(),
        dispatcher_policy=DispatcherPolicy(
            require_durable_idempotency_for_high_risk=durable_high_risk
        ),
    )


def test_request_deep_freezes_inputs_and_plan_step():
    request = _request(inputs={"nested": {"values": [1, 2]}})
    with pytest.raises(TypeError):
        request.inputs["new"] = 3  # type: ignore[index]
    with pytest.raises(TypeError):
        request.inputs["nested"]["x"] = 1  # type: ignore[index]
    assert request.inputs["nested"]["values"] == (1, 2)


def test_sticky_approval_fingerprint_changes_if_input_changes():
    resolver = StickyApprovalResolver()
    first = _request(inputs={"command": ["pytest"]})
    second = _request(inputs={"command": ["rm", "-rf", "x"]})
    f1 = resolver.fingerprint(first, ExecutorRiskClass.HIGH)
    f2 = resolver.fingerprint(second, ExecutorRiskClass.HIGH)
    assert f1 != f2
    resolver.grant(approval_id="approval-1", fingerprint=f1, approved_by="human")
    assert resolver.is_approved(approval_id="approval-1", fingerprint=f1)
    assert not resolver.is_approved(approval_id="approval-1", fingerprint=f2)


def test_sticky_approval_fingerprint_changes_if_permissions_or_credentials_change():
    resolver = StickyApprovalResolver()
    base = _request(granted_capabilities=("planning",))
    changed = _request(
        granted_capabilities=("planning", "routing"),
        credential_requirements=(
            CredentialRequirement("openai.api_key", "provider.openai", "reasoning"),
        ),
    )
    f1 = resolver.fingerprint(base, ExecutorRiskClass.READ_ONLY)
    f2 = resolver.fingerprint(changed, ExecutorRiskClass.READ_ONLY)
    assert f1 != f2


def test_immutable_execution_manifest_hash_is_stable():
    request = _request()
    resolver = StickyApprovalResolver()
    fp = resolver.fingerprint(request, ExecutorRiskClass.READ_ONLY)
    one = ImmutableExecutionManifest.freeze(
        request, risk_class=ExecutorRiskClass.READ_ONLY, approval_fingerprint=fp
    )
    two = ImmutableExecutionManifest.freeze(
        request, risk_class=ExecutorRiskClass.READ_ONLY, approval_fingerprint=fp
    )
    assert one.manifest_hash == two.manifest_hash
    assert one.input_hash == two.input_hash


@pytest.mark.asyncio
async def test_dispatcher_fail_closed_when_no_executor(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path)
    result = await dispatcher.execute(_request())
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error == "no_capable_executor"
    assert result.manifest_hash
    assert result.evidence_refs
    assert dispatcher.ledger.verify().valid is True


@pytest.mark.asyncio
async def test_read_only_executor_runs_after_pre_audit_and_final_audit(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path)
    executor = _Executor()
    dispatcher.register(executor)
    result = await dispatcher.execute(_request())
    assert result.status is ExecutionStatus.SUCCEEDED
    assert executor.calls == 1
    assert len(result.evidence_refs) == 2
    assert dispatcher.ledger.verify().entries == 2


@pytest.mark.asyncio
async def test_kill_switch_hierarchy_blocks_before_executor(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path)
    executor = _Executor()
    dispatcher.register(executor)
    dispatcher.kill_switches.skills.add("brain.plan")
    result = await dispatcher.execute(_request())
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error == "kill_switch_skill"
    assert executor.calls == 0


@pytest.mark.asyncio
async def test_manifest_executor_mismatch_is_blocked(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path)
    result = await dispatcher.execute(_request(executor=ExecutorType.PROVIDER))
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error == "executor_manifest_mismatch"


@pytest.mark.asyncio
async def test_executable_skill_requires_explicit_capability_grants(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path, durable_high_risk=False)
    request = _request(
        "hands.code_patch", executor=ExecutorType.SANDBOX, idempotency_key="patch-perm"
    )
    result = await dispatcher.execute(request)
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error.startswith("missing_capability_grant:")


@pytest.mark.asyncio
async def test_high_risk_requires_sticky_approval_before_any_execution(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path, durable_high_risk=False)
    request = _request(
        "hands.code_patch",
        executor=ExecutorType.SANDBOX,
        idempotency_key="patch-1",
        granted_capabilities=("code_write", "patch"),
    )
    result = await dispatcher.execute(request)
    assert result.status is ExecutionStatus.WAITING_APPROVAL
    assert result.error == "sticky_approval_required_or_mismatch"


@pytest.mark.asyncio
async def test_high_risk_is_blocked_by_non_durable_idempotency_even_when_approved(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path)
    request_without_approval = _request(
        "hands.code_patch",
        executor=ExecutorType.SANDBOX,
        idempotency_key="patch-1",
        granted_capabilities=("code_write", "patch"),
    )
    fp = dispatcher.approval.fingerprint(request_without_approval, ExecutorRiskClass.HIGH)
    dispatcher.approval.grant(approval_id="approval-1", fingerprint=fp, approved_by="human")
    request = _request(
        "hands.code_patch",
        executor=ExecutorType.SANDBOX,
        approval_id="approval-1",
        idempotency_key="patch-1",
        granted_capabilities=("code_write", "patch"),
    )
    # Fingerprint includes approval-independent execution facts, so the grant remains valid.
    assert dispatcher.approval.fingerprint(request, ExecutorRiskClass.HIGH) == fp
    result = await dispatcher.execute(request)
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error == "durable_idempotency_required_for_high_risk"


@pytest.mark.asyncio
async def test_production_write_remains_blocked_even_with_approval(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path, durable_high_risk=False)
    request = _request(
        "hands.code_patch",
        executor=ExecutorType.SANDBOX,
        environment="production",
        idempotency_key="patch-prod",
        granted_capabilities=("code_write", "patch"),
    )
    fp = dispatcher.approval.fingerprint(request, ExecutorRiskClass.HIGH)
    dispatcher.approval.grant(approval_id="approval-prod", fingerprint=fp, approved_by="human")
    request = _request(
        "hands.code_patch",
        executor=ExecutorType.SANDBOX,
        environment="production",
        approval_id="approval-prod",
        idempotency_key="patch-prod",
        granted_capabilities=("code_write", "patch"),
    )
    result = await dispatcher.execute(request)
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error == "production_mutation_disabled"


@pytest.mark.asyncio
async def test_executor_risk_escalation_invalidates_manifest_scope(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path)
    executor = _Executor(risk_class=ExecutorRiskClass.HIGH)
    dispatcher.register(executor)
    result = await dispatcher.execute(_request())
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error == "executor_risk_escalation_requires_new_manifest_and_approval"
    assert executor.calls == 0


@pytest.mark.asyncio
async def test_credential_lease_forbids_user_sourced_secret(tmp_path: Path):
    broker = CredentialBroker(policy={"provider.openai": frozenset({CredentialId.OPENAI_API_KEY})})
    broker.put_ephemeral(
        CredentialId.OPENAI_API_KEY,
        "not-a-real-secret",
        source="user-provided",
    )
    dispatcher = _dispatcher(tmp_path, credential_broker=broker)
    request = _request(
        credential_requirements=(
            CredentialRequirement("openai.api_key", "provider.openai", "test-only-provider-call"),
        )
    )
    result = await dispatcher.execute(request)
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error == "credential_lease_blocked:CredentialLeaseDenied"


@pytest.mark.asyncio
async def test_idempotency_manifest_conflict_blocks_reuse(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path)
    executor = _Executor()
    dispatcher.register(executor)
    first = await dispatcher.execute(_request(inputs={"value": 1}))
    assert first.status is ExecutionStatus.SUCCEEDED
    second = await dispatcher.execute(_request(inputs={"value": 2}))
    assert second.status is ExecutionStatus.BLOCKED
    assert second.error == "idempotency_key_manifest_conflict"
    assert executor.calls == 1


def test_artifact_promotion_requires_all_intermediate_states():
    assert can_promote(ArtifactPromotionState.CANDIDATE, ArtifactPromotionState.VERIFIED)
    assert not can_promote(ArtifactPromotionState.CANDIDATE, ArtifactPromotionState.PROMOTED)
    assert can_promote(ArtifactPromotionState.APPROVED, ArtifactPromotionState.PROMOTED)
    assert CodePatchState.CANDIDATE_READY.value == "candidate_ready"


def test_agnes_status_exposes_security_baseline_without_sandbox(tmp_path: Path):
    agnes = AgnesNervousSystem(skill_file=_skill_file(), ledger_path=tmp_path / "ledger.jsonl")
    kernel = agnes.status()["execution_kernel"]
    assert kernel["agent_is_executor"] is False
    assert kernel["workspace_is_sandbox"] is False
    assert kernel["sandbox_executor_enabled"] is False
    assert kernel["fail_closed"] is True


def test_api_exposes_execution_kernel_status(tmp_path: Path):
    settings = Settings(
        mock_ai=True,
        database_path=tmp_path / "db.sqlite",
        agnes_ledger_path=tmp_path / "agnes.jsonl",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/agnes/execution/status")
        assert response.status_code == 200
        body = response.json()
        assert body["phase"] == "AGNES Execution Kernel Phase 1 — Security Baseline"
        assert body["sandbox_executor_enabled"] is False


@pytest.mark.asyncio
async def test_pre_audit_failure_prevents_executor_run(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path)
    executor = _Executor()
    dispatcher.register(executor)

    class _BrokenEvidence:
        def pre_audit(self, _manifest):
            raise OSError("audit unavailable")

        def finalize(self, _manifest, _result):  # pragma: no cover - must not run
            raise AssertionError("finalize should not run")

    dispatcher.evidence = _BrokenEvidence()
    result = await dispatcher.execute(_request())
    assert result.status is ExecutionStatus.BLOCKED
    assert result.error == "control_plane_failure:OSError"
    assert executor.calls == 0


@dataclass
class _BadResultExecutor(_Executor):
    async def execute(
        self, request: SkillExecutionRequest, context: ExecutionContext
    ) -> SkillExecutionResult:
        self.calls += 1
        return SkillExecutionResult(
            "wrong-execution-id",
            request.skill_id,
            ExecutionStatus.SUCCEEDED,
            output={"should_not_promote": True},
        )


@pytest.mark.asyncio
async def test_result_verification_rejects_executor_identity_mismatch(tmp_path: Path):
    dispatcher = _dispatcher(tmp_path)
    executor = _BadResultExecutor()
    dispatcher.register(executor)
    result = await dispatcher.execute(_request())
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "verification_failed:execution_id_mismatch"
    assert executor.calls == 1
    assert len(result.evidence_refs) == 2
