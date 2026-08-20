from __future__ import annotations

from typing import Any

import pytest

from creator_app.ai_team.ck_coordination import build_ck_v3_packet
from creator_app.ai_team.ck_v3_executor import (
    CKV3ExecutionGrant,
    CKV3ReadOnlyExecutor,
    ExecutionPolicyError,
    ExecutionStatus,
)
from creator_app.ai_team.ck_v3_planner import CKV3Planner

_NOW = 1_800_000_000


class FakeInvoker:
    def __init__(self, output: Any = None, *, fail: bool = False) -> None:
        self.output = {"ok": True} if output is None else output
        self.fail = fail
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        if self.fail:
            raise RuntimeError("do not leak this runtime detail")
        return self.output


class StaticGrantVerifier:
    def __init__(self, allowed: bool = True, *, fail: bool = False) -> None:
        self.allowed = allowed
        self.fail = fail
        self.seen: list[CKV3ExecutionGrant] = []

    async def verify_grant(self, grant: CKV3ExecutionGrant) -> bool:
        self.seen.append(grant)
        if self.fail:
            raise RuntimeError("broker detail must not escape")
        return self.allowed


class MemoryReplayGuard:
    def __init__(self) -> None:
        self.consumed: set[tuple[str, str]] = set()

    async def consume(self, *, grant_id: str, request_id: str, expires_at_unix: int) -> bool:
        assert expires_at_unix > _NOW
        key = (grant_id, request_id)
        if key in self.consumed:
            return False
        self.consumed.add(key)
        return True


def _plan(action: str = "tool:bridge_status"):
    packet = build_ck_v3_packet(
        task_id="CK3-EXEC-001",
        target="creator_app/device_bridge",
        objective="Run one bounded read-only tool step.",
        source_commit="a" * 40,
        allowed_actions=(action,),
        expected_evidence=("result digest", "runtime identity"),
    )
    return CKV3Planner.compile(packet)


def _grant(
    *,
    allowed_tools: tuple[str, ...] = ("bridge_status",),
    source_commit: str = "a" * 40,
    source_tree: str = "b" * 40,
    registry_sha256: str = "c" * 64,
    expires_at_unix: int = _NOW + 300,
) -> CKV3ExecutionGrant:
    return CKV3ExecutionGrant(
        grant_id="grant-001",
        task_id="CK3-EXEC-001",
        source_commit=source_commit,
        source_tree=source_tree,
        registry_sha256=registry_sha256,
        allowed_tools=allowed_tools,
        issued_at_unix=_NOW,
        expires_at_unix=expires_at_unix,
    )


async def _execute(
    *,
    action: str = "tool:bridge_status",
    request_id: str = "req-001",
    arguments: dict[str, Any] | None = None,
    grant: CKV3ExecutionGrant | None = None,
    grant_verifier: StaticGrantVerifier | None = None,
    replay_guard: MemoryReplayGuard | None = None,
    current_source_commit: str = "a" * 40,
    current_source_tree: str = "b" * 40,
    current_registry_sha256: str = "c" * 64,
    invoker: FakeInvoker | None = None,
):
    actual_invoker = FakeInvoker() if invoker is None else invoker
    actual_verifier = StaticGrantVerifier() if grant_verifier is None else grant_verifier
    actual_replay = MemoryReplayGuard() if replay_guard is None else replay_guard
    result = await CKV3ReadOnlyExecutor().execute(
        plan=_plan(action),
        step_id="CK3-EXEC-001-S01",
        request_id=request_id,
        arguments={} if arguments is None else arguments,
        grant=_grant() if grant is None else grant,
        grant_verifier=actual_verifier,
        replay_guard=actual_replay,
        current_source_commit=current_source_commit,
        current_source_tree=current_source_tree,
        current_registry_sha256=current_registry_sha256,
        invoker=actual_invoker,
        now_unix=_NOW,
    )
    return result, actual_invoker


@pytest.mark.asyncio
async def test_executor_runs_exact_granted_read_only_tool_and_emits_bounded_evidence() -> None:
    output = {"ok": True, "authority": "CK-NEXUS", "file_write": False}
    result, invoker = await _execute(invoker=FakeInvoker(output))

    assert result.ok is True
    assert result.output == output
    assert invoker.calls == [("bridge_status", {})]
    assert result.evidence.status is ExecutionStatus.PASS
    assert result.evidence.request_id == "req-001"
    assert result.evidence.tool_name == "bridge_status"
    assert result.evidence.source_commit == "a" * 40
    assert result.evidence.source_tree == "b" * 40
    assert result.evidence.registry_sha256 == "c" * 64
    assert result.evidence.evidence_id.startswith("evd_")
    assert len(result.evidence.argument_sha256) == 64
    assert len(result.evidence.result_sha256) == 64
    assert not hasattr(result.evidence, "arguments")


@pytest.mark.asyncio
async def test_executor_rejects_unverified_grant_before_tool_call() -> None:
    invoker = FakeInvoker()
    with pytest.raises(ExecutionPolicyError, match="grant_verification_failed"):
        await _execute(
            grant_verifier=StaticGrantVerifier(allowed=False),
            invoker=invoker,
        )
    assert invoker.calls == []

    with pytest.raises(ExecutionPolicyError, match="grant_verification_failed"):
        await _execute(
            grant_verifier=StaticGrantVerifier(fail=True),
            invoker=invoker,
        )
    assert invoker.calls == []


@pytest.mark.asyncio
async def test_executor_rejects_replayed_request_before_second_tool_call() -> None:
    replay = MemoryReplayGuard()
    invoker = FakeInvoker()
    first, _ = await _execute(replay_guard=replay, invoker=invoker)
    assert first.ok is True

    with pytest.raises(ExecutionPolicyError, match="request_replay_denied"):
        await _execute(replay_guard=replay, invoker=invoker)
    assert len(invoker.calls) == 1


@pytest.mark.asyncio
async def test_executor_rejects_stale_source_or_registry_before_tool_call() -> None:
    invoker = FakeInvoker()
    with pytest.raises(ExecutionPolicyError, match="stale_source_commit"):
        await _execute(current_source_commit="d" * 40, invoker=invoker)
    assert invoker.calls == []

    with pytest.raises(ExecutionPolicyError, match="stale_source_tree"):
        await _execute(current_source_tree="e" * 40, invoker=invoker)
    assert invoker.calls == []

    with pytest.raises(ExecutionPolicyError, match="stale_runtime_registry"):
        await _execute(current_registry_sha256="f" * 64, invoker=invoker)
    assert invoker.calls == []


@pytest.mark.asyncio
async def test_executor_requires_explicit_canonical_tool_action() -> None:
    invoker = FakeInvoker()
    with pytest.raises(ExecutionPolicyError, match="explicit_tool_action_required"):
        await _execute(action="inspect bridge status", invoker=invoker)
    assert invoker.calls == []

    with pytest.raises(ExecutionPolicyError, match="tool_not_canonical_read_only"):
        await _execute(action="tool:solve_system", invoker=invoker)
    assert invoker.calls == []


@pytest.mark.asyncio
async def test_executor_requires_tool_to_be_present_in_short_lived_grant() -> None:
    invoker = FakeInvoker()
    with pytest.raises(ExecutionPolicyError, match="tool_not_granted"):
        await _execute(
            action="tool:workspace_list",
            grant=_grant(allowed_tools=("bridge_status",)),
            invoker=invoker,
        )
    assert invoker.calls == []


@pytest.mark.asyncio
async def test_executor_denies_sensitive_argument_keys_before_invocation() -> None:
    invoker = FakeInvoker()
    with pytest.raises(ExecutionPolicyError, match="sensitive_argument_key_denied"):
        await _execute(
            arguments={"nested": {"authorization": "not-a-real-secret"}},
            invoker=invoker,
        )
    assert invoker.calls == []

    with pytest.raises(ExecutionPolicyError, match="sensitive_argument_key_denied"):
        await _execute(
            request_id="req-002",
            arguments={"client-secret": "placeholder"},
            invoker=invoker,
        )
    assert invoker.calls == []


@pytest.mark.asyncio
async def test_executor_denies_oversized_arguments_before_invocation() -> None:
    invoker = FakeInvoker()
    with pytest.raises(ExecutionPolicyError, match="tool_arguments_too_large"):
        await _execute(arguments={"data": "x" * 9000}, invoker=invoker)
    assert invoker.calls == []


@pytest.mark.asyncio
async def test_executor_fails_closed_without_leaking_invoker_exception() -> None:
    result, invoker = await _execute(invoker=FakeInvoker(fail=True))

    assert len(invoker.calls) == 1
    assert result.ok is False
    assert result.output == {"ok": False, "error": "tool_call_failed_closed"}
    assert result.evidence.status is ExecutionStatus.FAIL
    assert result.evidence.error == "tool_call_failed_closed"


@pytest.mark.asyncio
async def test_executor_fails_closed_on_oversized_result_without_returning_content() -> None:
    result, invoker = await _execute(invoker=FakeInvoker({"data": "x" * 17000}))

    assert len(invoker.calls) == 1
    assert result.ok is False
    assert result.output == {"ok": False, "error": "tool_result_too_large"}
    assert result.evidence.status is ExecutionStatus.FAIL
    assert result.evidence.result_bytes > 16 * 1024
    assert len(result.evidence.result_sha256) == 64


def test_grant_rejects_noncanonical_tools_or_unsafe_authority_flags() -> None:
    with pytest.raises(ExecutionPolicyError, match="noncanonical_tool_in_grant"):
        _grant(allowed_tools=("solve_system",)).validate(now_unix=_NOW)

    unsafe = CKV3ExecutionGrant(
        grant_id="grant-unsafe",
        task_id="CK3-EXEC-001",
        source_commit="a" * 40,
        source_tree="b" * 40,
        registry_sha256="c" * 64,
        allowed_tools=("bridge_status",),
        issued_at_unix=_NOW,
        expires_at_unix=_NOW + 300,
        production_mutation=True,
    )
    with pytest.raises(ExecutionPolicyError, match="production_mutation_denied"):
        unsafe.validate(now_unix=_NOW)


def test_grant_rejects_expired_or_long_lived_window() -> None:
    with pytest.raises(ExecutionPolicyError, match="grant_expired"):
        _grant(expires_at_unix=_NOW).validate(now_unix=_NOW)

    with pytest.raises(ExecutionPolicyError, match="grant_ttl_invalid"):
        _grant(expires_at_unix=_NOW + 3600).validate(now_unix=_NOW)