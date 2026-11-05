import asyncio
from types import SimpleNamespace

from creator_app.ai_team.intelligence.parallel_executor import ParallelExecutor
from creator_app.control_plane.models import ExecutionState
from creator_app.control_plane.orchestrator import ControlPlaneOrchestrator


def test_dispatch_runs_ready_nodes_and_waits_for_dependencies() -> None:
    graph = ControlPlaneOrchestrator().plan("improve MCP routing")
    events: list[str] = []

    async def run() -> object:
        executor = ParallelExecutor(max_concurrency=2)
        return await ControlPlaneOrchestrator().dispatch(
            graph,
            handlers={
                "research": lambda node: events.append(node.role) or "research-ok",
                "implementation": lambda node: events.append(node.role) or "implementation-ok",
                "verification": lambda node: events.append(node.role) or "verification-ok",
                "security": lambda node: events.append(node.role) or "security-ok",
            },
            parallel_executor=executor,
        )

    result = asyncio.run(run())
    assert result.execution_state is ExecutionState.COMPLETED
    assert set(result.results) == {node.node_id for node in graph.nodes}
    assert events.index("implementation") < events.index("verification")
    assert events.index("implementation") < events.index("security")


def test_dispatch_stops_downstream_after_failed_dependency() -> None:
    graph = ControlPlaneOrchestrator().plan("repair API")

    async def run() -> object:
        return await ControlPlaneOrchestrator().dispatch(
            graph,
            handlers={
                "research": lambda _node: "research-ok",
                "implementation": lambda _node: (_ for _ in ()).throw(RuntimeError("boom")),
                "verification": lambda _node: "should-not-run",
                "security": lambda _node: "should-not-run",
            },
        )

    result = asyncio.run(run())
    assert result.execution_state is ExecutionState.FAILED
    assert result.results["task-02-implementation"]["state"] == "failed"
    assert result.results["task-03-verification"]["state"] == "blocked_dependency"
    assert result.results["task-04-security"]["state"] == "blocked_dependency"


def test_default_handlers_delegate_to_existing_team_director() -> None:
    class FakeTeam:
        def process_request(
            self, description: str, *, priority: int, context: str, evidence_bundle=None
        ):
            return SimpleNamespace(
                final_output=f"handled:{description}",
                status=SimpleNamespace(value="completed"),
                team_members_used=("engineer",),
                confidence=0.9,
            )

    orchestrator = ControlPlaneOrchestrator(team_director=FakeTeam())
    handler = orchestrator.default_handlers()["implementation"]
    result = handler(orchestrator.plan("build feature").nodes[1])
    assert result["final_output"].startswith("handled:")
    assert result["team_members_used"] == ["engineer"]


def test_dispatch_fails_closed_for_cyclic_or_empty_graphs() -> None:
    from creator_app.control_plane.models import ControlPlaneRequest, TaskGraph, TaskNode

    orchestrator = ControlPlaneOrchestrator()
    cyclic = TaskGraph(
        request=ControlPlaneRequest(description="cycle test"),
        nodes=(
            TaskNode(node_id="a", role="research", task="a", depends_on=("b",)),
            TaskNode(node_id="b", role="implementation", task="b", depends_on=("a",)),
        ),
    )
    empty = TaskGraph(request=ControlPlaneRequest(description="empty test"), nodes=())

    async def run() -> tuple[object, object]:
        return await orchestrator.dispatch(cyclic, handlers={}), await orchestrator.dispatch(empty)

    cycle_result, empty_result = asyncio.run(run())
    assert cycle_result.execution_state is ExecutionState.FAILED
    assert all(item["state"] == "blocked_dependency" for item in cycle_result.results.values())
    assert empty_result.execution_state is ExecutionState.FAILED
    assert empty_result.results == {}


def test_plan_can_be_adapted_to_queue_payload_without_production_authority() -> None:
    graph = ControlPlaneOrchestrator().plan("queue safe worker")
    payload = graph.as_queue_payload("task-02-implementation")
    assert payload["handler"] == "implementation"
    assert payload["node_id"] == "task-02-implementation"
    assert payload["depends_on"] == ["task-01-research"]
    assert payload["production_status"] == "NO-GO"
    assert payload["external_mutation_authorized"] is False
    assert payload["release_evidence"] is False


def test_queue_adapter_rejects_unknown_node() -> None:
    graph = ControlPlaneOrchestrator().plan("queue safe worker")
    try:
        graph.as_queue_payload("missing-node")
    except ValueError as exc:
        assert "unknown task node" in str(exc)
    else:
        raise AssertionError("unknown node must be rejected")


def test_dispatch_preserves_blocked_team_result_and_blocks_dependents() -> None:
    from types import SimpleNamespace

    class BlockedTeam:
        def process_request(
            self, description: str, *, priority: int, context: str, evidence_bundle=None
        ):
            return SimpleNamespace(
                final_output="NO EVIDENCE → NO DONE",
                status=SimpleNamespace(value="blocked"),
                team_members_used=("Sentinel",),
                confidence=0.0,
            )

    orchestrator = ControlPlaneOrchestrator(team_director=BlockedTeam())
    graph = orchestrator.plan("verify release evidence")
    result = asyncio.run(orchestrator.dispatch(graph))

    assert result.execution_state is ExecutionState.BLOCKED
    assert result.results["task-01-research"]["state"] == "blocked"
    assert result.results["task-02-implementation"]["state"] == "blocked_dependency"
    assert result.results["task-03-verification"]["state"] == "blocked_dependency"
    assert result.results["task-04-security"]["state"] == "blocked_dependency"


def test_control_plane_forwards_evidence_bundle_to_team_director() -> None:
    from types import SimpleNamespace

    class CapturingTeam:
        received = None

        def process_request(
            self, description: str, *, priority: int, context: str, evidence_bundle=None
        ):
            self.received = evidence_bundle
            return SimpleNamespace(
                final_output="candidate",
                status=SimpleNamespace(value="blocked"),
                team_members_used=("Sentinel",),
                confidence=0.1,
            )

    bundle = {"subject_sha": "a" * 40, "checks": []}
    team = CapturingTeam()
    orchestrator = ControlPlaneOrchestrator(team_director=team)
    graph = orchestrator.plan("verify release evidence", evidence_bundle=bundle)
    research_node = next(node for node in graph.nodes if node.role == "research")
    security_node = next(node for node in graph.nodes if node.role == "security")

    assert research_node.evidence_bundle is None
    assert security_node.evidence_bundle == bundle
    assert security_node.evidence_bundle is not bundle

    orchestrator.default_handlers()["research"](research_node)
    assert team.received is None
    orchestrator.default_handlers()["security"](security_node)
    assert team.received == bundle
    assert team.received is not bundle


def test_default_dispatch_does_not_require_evidence_for_ordinary_verification() -> None:
    graph = ControlPlaneOrchestrator().plan("improve MCP routing")
    result = asyncio.run(ControlPlaneOrchestrator().dispatch(graph))

    assert result.execution_state is ExecutionState.COMPLETED
    assert all(item["state"] == "completed" for item in result.results.values())


def test_explicit_evidence_gate_without_bundle_fails_closed() -> None:
    graph = ControlPlaneOrchestrator().plan("verify release evidence")
    result = asyncio.run(ControlPlaneOrchestrator().dispatch(graph))

    assert result.execution_state is ExecutionState.BLOCKED
    assert result.results["task-01-research"]["state"] == "completed"
    assert result.results["task-02-implementation"]["state"] == "completed"
    assert result.results["task-03-verification"]["state"] == "completed"
    assert result.results["task-04-security"]["state"] == "blocked"


def test_dispatch_blocks_non_dict_results_with_empty_status() -> None:
    graph = ControlPlaneOrchestrator().plan("repair API")

    async def run() -> object:
        return await ControlPlaneOrchestrator().dispatch(
            graph,
            handlers={
                "research": lambda _node: SimpleNamespace(status=None),
                "implementation": lambda _node: "must-not-run",
                "verification": lambda _node: "must-not-run",
                "security": lambda _node: "must-not-run",
            },
        )

    result = asyncio.run(run())
    assert result.execution_state is ExecutionState.BLOCKED
    assert result.results["task-01-research"]["state"] == "blocked"
    assert result.results["task-02-implementation"]["state"] == "blocked_dependency"


def test_dispatch_reads_status_from_non_dict_result_objects() -> None:
    graph = ControlPlaneOrchestrator().plan("repair API")

    async def run() -> object:
        return await ControlPlaneOrchestrator().dispatch(
            graph,
            handlers={
                "research": lambda _node: SimpleNamespace(
                    status=SimpleNamespace(value="blocked")
                ),
                "implementation": lambda _node: "must-not-run",
                "verification": lambda _node: "must-not-run",
                "security": lambda _node: "must-not-run",
            },
        )

    result = asyncio.run(run())
    assert result.execution_state is ExecutionState.BLOCKED
    assert result.results["task-01-research"]["state"] == "blocked"
    assert result.results["task-02-implementation"]["state"] == "blocked_dependency"
    assert result.results["task-03-verification"]["state"] == "blocked_dependency"
    assert result.results["task-04-security"]["state"] == "blocked_dependency"


def test_control_plane_security_handler_routes_supplied_bundle_to_sentinel() -> None:
    subject_sha = "a" * 40
    bundle = {
        "subject_sha": subject_sha,
        "source": "https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/123",
        "observed_at": "2026-11-05T03:00:00Z",
        "checks": [
            {
                "name": "ci",
                "status": "PASS",
                "subject_sha": subject_sha,
                "evidence_ref": "https://github.com/CK-NEXUS-AI/ck-nexus/actions/runs/123",
                "artifact_sha256": "b" * 64,
            }
        ],
    }
    orchestrator = ControlPlaneOrchestrator()
    graph = orchestrator.plan("inspect artifact", evidence_bundle=bundle)
    security_node = next(node for node in graph.nodes if node.role == "security")

    result = orchestrator.default_handlers()["security"](security_node)

    assert result["status"] == "blocked"
    assert "Sentinel" in result["team_members_used"]
    assert "Core/L3" in result["final_output"]
