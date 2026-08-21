import pytest

from creator_app.core.policy_errors import PolicyViolation
from creator_app.core.resilience_faults import (
    ChaosScenarioRunner,
    FaultPlan,
    FaultSpec,
    FaultTarget,
    FaultType,
)


class RecordingAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def inject(self, fault: FaultSpec) -> dict[str, object]:
        self.calls.append(fault.fault_id)
        return {"fault_id": fault.fault_id, "injected": True}


def build_plan(*, attested: bool, granted: bool) -> FaultPlan:
    return FaultPlan(
        seed=42,
        sandbox_attested=attested,
        execution_grant_id="grant:chaos" if granted else None,
        faults=[
            FaultSpec(
                fault_id="fault:disk-full",
                fault_type=FaultType.DISK_FULL,
                target=FaultTarget.STATE_STORE,
                severity=2,
                duration_ms=1000,
            )
        ],
    )


def test_chaos_plan_is_deterministic() -> None:
    first = build_plan(attested=True, granted=True)
    second = build_plan(attested=True, granted=True)

    assert first.digest() == second.digest()


def test_chaos_requires_sandbox_attestation() -> None:
    adapter = RecordingAdapter()
    with pytest.raises(PolicyViolation):
        ChaosScenarioRunner(adapter).run(build_plan(attested=False, granted=True))
    assert adapter.calls == []


def test_chaos_requires_execution_grant() -> None:
    adapter = RecordingAdapter()
    with pytest.raises(PolicyViolation):
        ChaosScenarioRunner(adapter).run(build_plan(attested=True, granted=False))
    assert adapter.calls == []


def test_chaos_dispatches_only_after_all_gates_pass() -> None:
    adapter = RecordingAdapter()
    result = ChaosScenarioRunner(adapter).run(build_plan(attested=True, granted=True))

    assert result == [{"fault_id": "fault:disk-full", "injected": True}]
    assert adapter.calls == ["fault:disk-full"]
