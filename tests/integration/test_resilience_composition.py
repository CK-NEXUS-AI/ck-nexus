from datetime import UTC, datetime

from creator_app.core.deterministic_state import DeterministicState
from creator_app.core.mock_provider import MockRequest, StandardMockProvider
from creator_app.core.resilience_evidence import HashLinkedEvidenceStore
from creator_app.core.resilience_faults import (
    ChaosScenarioRunner,
    FaultPlan,
    FaultSpec,
    FaultTarget,
    FaultType,
)


class MockFaultAdapter:
    def inject(self, fault: FaultSpec) -> dict[str, object]:
        return {"fault_id": fault.fault_id, "status": "simulated"}


def test_resilience_flow_is_deterministic_and_evidence_backed(tmp_path) -> None:
    deterministic = DeterministicState(seed=42)
    provider = StandardMockProvider()
    evidence = HashLinkedEvidenceStore(tmp_path / "resilience-evidence.jsonl")

    provider_result = provider.execute(MockRequest(operation="health"))
    scenario = deterministic.choice(
        key="resilience:scenario",
        options=[FaultType.LATENCY, FaultType.SERVICE_UNAVAILABLE],
    )
    plan = FaultPlan(
        seed=42,
        sandbox_attested=True,
        execution_grant_id="grant:test-only",
        faults=[
            FaultSpec(
                fault_id="fault:1",
                fault_type=scenario,
                target=FaultTarget.PROVIDER,
            )
        ],
    )
    fault_results = ChaosScenarioRunner(MockFaultAdapter()).run(plan)
    payload = {
        "provider": provider_result.model_dump(mode="json"),
        "fault_plan_digest": plan.digest(),
        "fault_results": fault_results,
    }
    evidence.append(
        event_type="resilience.simulation.completed",
        subject="integration:nexus-omni",
        payload_digest=evidence.payload_digest(payload),
        created_at=datetime(2026, 8, 21, 10, tzinfo=UTC),
    )

    assert provider_result.status_code == 200
    assert fault_results == [{"fault_id": "fault:1", "status": "simulated"}]
    assert evidence.verify_chain() is True
